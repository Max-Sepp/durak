from __future__ import annotations

import copy
import random

from .actions import Action, Attack, Defend, Pass, SwapTrump, Take, Transfer
from .cards import Card, lowest_rank, make_deck
from .config import GameConfig
from .errors import IllegalAction
from .state import GameState, Phase, TablePair
from .views import Event, PlayerView


class Game:
    """Rules engine for Podkidnoy / Perevodnoy Durak.

    The engine has no knowledge of networking: callers ask for `legal_actions`,
    submit moves with `apply`, and render `view`. Several players may have legal
    moves at the same time (throw-ins), so callers must serialise `apply` calls.
    """

    def __init__(self, state: GameState) -> None:
        self.state = state

    # ------------------------------------------------------------------ setup

    @classmethod
    def new(cls, config: GameConfig, seed: int | None = None) -> Game:
        # Real games shuffle with the OS CSPRNG: Mersenne Twister state can be
        # reconstructed from observed output, which would let a player predict
        # the deck. A seed gives reproducible shuffles for tests and AI training.
        rng = random.SystemRandom() if seed is None else random.Random(seed)
        deck = make_deck(config.deck_size, rng)
        hands: list[list[Card]] = [[] for _ in range(config.num_players)]
        for _ in range(config.hand_size):
            for hand in hands:
                hand.append(deck.pop())
        # With a full table (e.g. 6 players, 36 cards) the talon is empty and the
        # last card dealt decides the trump suit.
        trump_card = deck[0] if deck else hands[-1][-1]
        attacker = _lowest_trump_holder(hands, trump_card)
        defender = (attacker + 1) % config.num_players
        state = GameState(
            config=config,
            hands=hands,
            talon=deck,
            trump_card=trump_card,
            attacker=attacker,
            defender=defender,
            bout_limit=min(config.first_bout_limit, len(hands[defender])),
        )
        return cls(state)

    def clone(self) -> Game:
        return Game(copy.deepcopy(self.state))

    # ---------------------------------------------------------------- queries

    @property
    def finished(self) -> bool:
        return self.state.phase is Phase.FINISHED

    def active_players(self) -> list[int]:
        out = set(self.state.out_order)
        return [p for p in range(self.state.num_players) if p not in out]

    def current_actors(self) -> set[int]:
        return {p for p in range(self.state.num_players) if self.legal_actions(p)}

    def legal_actions(self, player: int) -> list[Action]:
        s = self.state
        if s.phase is Phase.FINISHED or player in s.out_order:
            return []
        actions = self._play_actions(player)
        if self._swap_card(player) is not None:
            actions.append(SwapTrump())
        return actions

    def _play_actions(self, player: int) -> list[Action]:
        s = self.state
        hand = s.hands[player]

        if player == s.defender:
            if s.phase is not Phase.ATTACKING or not s.table:
                return []
            options: list[Action] = []
            for i, pair in enumerate(s.table):
                if pair.defense is None:
                    options.extend(
                        Defend(i, c) for c in hand if c.beats(pair.attack, s.trump_suit)
                    )
            options.extend(Transfer(c) for c in self._transfer_cards())
            if any(pair.defense is None for pair in s.table):
                options.append(Take())
            return options

        if not s.table:
            if player == s.attacker and s.phase is Phase.ATTACKING:
                return [Attack(c) for c in hand]
            return []

        # Players with nothing to throw in are treated as having passed already.
        if player in s.passed:
            return []
        actions: list[Action] = [Attack(c) for c in self._throw_in_cards(player)]
        all_beaten = all(pair.defense is not None for pair in s.table)
        if actions and (s.phase is Phase.DEFENDER_TAKING or all_beaten):
            actions.append(Pass())
        return actions

    def view(self, player: int) -> PlayerView:
        s = self.state
        return PlayerView(
            you=player,
            hand=sorted(s.hands[player], key=lambda c: (c.suit == s.trump_suit, c.suit.value, c.rank)),
            hand_counts=[len(h) for h in s.hands],
            talon_count=len(s.talon),
            trump_card=s.trump_card if s.talon else None,
            trump_suit=s.trump_suit.value,
            table=[(pair.attack, pair.defense) for pair in s.table],
            attacker=s.attacker,
            defender=s.defender,
            phase=s.phase.value,
            passed=sorted(s.passed),
            out_order=list(s.out_order),
            durak=s.durak,
            winner=s.winner,
            discard_count=len(s.discard),
            bout_limit=s.bout_limit,
            transfer_enabled=s.config.transfer_enabled,
        )

    # ---------------------------------------------------------------- actions

    def apply(self, player: int, action: Action) -> list[Event]:
        if action not in self.legal_actions(player):
            raise IllegalAction(f"player {player} cannot play {action!r}")
        s = self.state
        events: list[Event] = []

        match action:
            case Attack(card):
                s.hands[player].remove(card)
                s.table.append(TablePair(card))
                s.passed.clear()
                events.append(Event("attack", player, {"card": str(card)}))
            case Defend(index, card):
                s.hands[player].remove(card)
                s.table[index].defense = card
                events.append(Event("defend", player, {"card": str(card), "attack_index": index}))
            case Transfer(card):
                s.hands[player].remove(card)
                s.table.append(TablePair(card))
                s.attacker = player
                s.defender = self._next_active(player)
                s.bout_limit = self._limit_for(s.defender)
                s.passed.clear()
                events.append(Event("transfer", player, {"card": str(card), "to": s.defender}))
            case Take():
                s.phase = Phase.DEFENDER_TAKING
                s.passed.clear()
                events.append(Event("take", player))
            case Pass():
                s.passed.add(player)
                events.append(Event("pass", player))
            case SwapTrump():
                low = self._swap_card(player)
                assert low is not None
                s.hands[player].remove(low)
                s.hands[player].append(s.trump_card)
                events.append(
                    Event("trump_swap", player, {"card": str(low), "took": str(s.trump_card)})
                )
                s.talon[0] = s.trump_card = low

        if not s.hands[player] and player not in s.emptied:
            s.emptied.append(player)
            # Nothing left to draw, so this player is the first out.
            if s.config.first_out_wins and not s.talon:
                return events + self._declare_winner(player)

        events.extend(self._maybe_end_bout())
        return events

    # -------------------------------------------------------------- internals

    def _swap_card(self, player: int) -> Card | None:
        """The lowest trump in `player`'s hand, if they may swap it for the face-up trump."""
        s = self.state
        if not s.config.trump_swap_enabled or not s.talon or s.talon[0] != s.trump_card:
            return None
        low = Card(lowest_rank(s.config.deck_size), s.trump_suit)
        if low == s.trump_card or low not in s.hands[player]:
            return None
        return low

    def _attack_count(self) -> int:
        return len(self.state.table)

    def _throw_in_cards(self, player: int) -> list[Card]:
        s = self.state
        if self._attack_count() >= s.bout_limit:
            return []
        if not s.config.all_players_throw_in and player != s.attacker:
            return []
        if not s.config.throw_in_after_take and s.phase is Phase.DEFENDER_TAKING:
            return []
        ranks = {pair.attack.rank for pair in s.table}
        ranks |= {pair.defense.rank for pair in s.table if pair.defense is not None}
        return [c for c in s.hands[player] if c.rank in ranks]

    def _transfer_cards(self) -> list[Card]:
        s = self.state
        if not s.config.transfer_enabled or s.phase is not Phase.ATTACKING or not s.table:
            return []
        if any(pair.defense is not None for pair in s.table):
            return []
        ranks = {pair.attack.rank for pair in s.table}
        if len(ranks) != 1:
            return []
        new_count = self._attack_count() + 1
        cap = s.config.first_bout_limit if s.is_first_bout else s.config.max_bout_cards
        target = self._next_active(s.defender)
        if new_count > cap or len(s.hands[target]) < new_count:
            return []
        (rank,) = ranks
        return [c for c in s.hands[s.defender] if c.rank == rank]

    def _limit_for(self, defender: int) -> int:
        s = self.state
        cap = s.config.first_bout_limit if s.is_first_bout else s.config.max_bout_cards
        return min(cap, len(s.hands[defender]))

    def _next_active(self, player: int) -> int:
        s = self.state
        out = set(s.out_order)
        for step in range(1, s.num_players + 1):
            candidate = (player + step) % s.num_players
            if candidate not in out:
                return candidate
        raise RuntimeError("no active players")

    def _waiting_on_throw_ins(self) -> bool:
        """True while some non-defender could still add a card and hasn't passed."""
        s = self.state
        return any(
            self._throw_in_cards(p)
            for p in self.active_players()
            if p != s.defender and p not in s.passed
        )

    def _maybe_end_bout(self) -> list[Event]:
        s = self.state
        if not s.table or self._waiting_on_throw_ins():
            return []
        if s.phase is Phase.ATTACKING:
            if any(pair.defense is None for pair in s.table):
                return []
            return self._finish_bout(taken=False)
        if s.phase is Phase.DEFENDER_TAKING:
            return self._finish_bout(taken=True)
        return []

    def _finish_bout(self, taken: bool) -> list[Event]:
        s = self.state
        cards = [pair.attack for pair in s.table]
        cards += [pair.defense for pair in s.table if pair.defense is not None]
        events: list[Event]
        if taken:
            s.hands[s.defender].extend(cards)
            events = [Event("bout_taken", s.defender, {"count": len(cards)})]
        else:
            s.discard.extend(cards)
            events = [Event("bout_beaten", s.defender, {"count": len(cards)})]
        s.table.clear()
        s.passed.clear()
        s.phase = Phase.ATTACKING
        s.is_first_bout = False

        events.extend(self._draw_cards())
        if s.config.first_out_wins and not s.talon:
            # The deck ran out before refilling everyone who emptied their hand
            # this bout; whoever got their cards down first wins.
            empty = [p for p in s.emptied if not s.hands[p]]
            if empty:
                return events + self._declare_winner(empty[0])
        s.emptied.clear()

        events.extend(self._eliminate_finished())

        active = self.active_players()
        if len(active) <= 1:
            s.phase = Phase.FINISHED
            s.durak = active[0] if active else None
            events.append(Event("game_over", s.durak))
            return events

        if taken or s.defender in s.out_order:
            s.attacker = self._next_active(s.defender)
        else:
            s.attacker = s.defender
        s.defender = self._next_active(s.attacker)
        s.bout_limit = self._limit_for(s.defender)
        events.append(Event("new_bout", s.attacker, {"defender": s.defender}))
        return events

    def _draw_cards(self) -> list[Event]:
        s = self.state
        order = [s.attacker]
        for step in range(1, s.num_players):
            p = (s.attacker + step) % s.num_players
            if p != s.defender and p not in s.out_order:
                order.append(p)
        order.append(s.defender)

        events: list[Event] = []
        for p in order:
            drawn = 0
            while s.talon and len(s.hands[p]) < s.config.hand_size:
                s.hands[p].append(s.talon.pop())
                drawn += 1
            if drawn:
                events.append(Event("draw", p, {"count": drawn}))
        return events

    def _declare_winner(self, player: int) -> list[Event]:
        s = self.state
        s.out_order.append(player)
        s.phase = Phase.FINISHED
        s.winner = player
        return [Event("player_out", player), Event("game_won", player)]

    def _eliminate_finished(self) -> list[Event]:
        s = self.state
        if s.talon:
            return []
        events: list[Event] = []
        for step in range(s.num_players):
            p = (s.attacker + step) % s.num_players
            if p not in s.out_order and not s.hands[p]:
                s.out_order.append(p)
                events.append(Event("player_out", p))
        return events


def _lowest_trump_holder(hands: list[list[Card]], trump_card: Card) -> int:
    best: tuple[int, int] | None = None
    for player, hand in enumerate(hands):
        for card in hand:
            if card.suit == trump_card.suit and (best is None or card.rank < best[0]):
                best = (card.rank, player)
    return best[1] if best else 0
