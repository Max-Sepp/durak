from __future__ import annotations

from durak_engine import Card, Event, GameConfig, PlayerView, make_deck


class CardTracker:
    """Public card memory for one seat, rebuilt from events.

    `PlayerView` only shows the current table and counts. Anything a player could
    remember by watching the game (the discard pile, cards someone picked up, the
    trump card someone swapped or drew) is tracked here.
    """

    def __init__(self, seat: int, config: GameConfig, view: PlayerView) -> None:
        self.seat = seat
        self.deck = frozenset(make_deck(config.deck_size))
        self.table: list[list[Card | None]] = []  # [attack, defense] pairs
        self.discard: set[Card] = set()
        self.known: list[set[Card]] = [set() for _ in range(config.num_players)]
        self.hand: list[Card] = []
        self.hand_counts: list[int] = []
        self.talon_count = 0
        self.face_up: Card | None = None
        # PlayerView doesn't say whether this is the first bout (which has a lower
        # card limit), so remember whether any bout has finished.
        initial_talon = config.deck_size - config.num_players * config.hand_size
        self.first_bout = view.discard_count == 0 and view.talon_count == initial_talon
        self._sync(view)

    # ---------------------------------------------------------------- queries

    def table_cards(self) -> set[Card]:
        return {c for pair in self.table for c in pair if c is not None}

    def unknown_count(self, player: int) -> int:
        """Cards in `player`'s hand that this seat hasn't seen."""
        return self.hand_counts[player] - len(self.known[player])

    def unseen(self) -> set[Card]:
        """Cards whose location this seat can't know: hidden in opponents' hands
        or face down in the talon."""
        seen = set(self.hand) | self.table_cards() | self.discard
        for player, cards in enumerate(self.known):
            if player != self.seat:
                seen |= cards
        if self.face_up is not None:
            seen.add(self.face_up)
        return set(self.deck - seen)

    # ---------------------------------------------------------------- updates

    def update(self, view: PlayerView, events: list[Event]) -> None:
        for event in events:
            self._apply(event)
        self._sync(view)

    def _sync(self, view: PlayerView) -> None:
        self.hand = list(view.hand)
        self.hand_counts = list(view.hand_counts)
        self.talon_count = view.talon_count
        self.face_up = view.trump_card
        self.table = [[attack, defense] for attack, defense in view.table]

    def _apply(self, event: Event) -> None:
        player = event.player
        match event.kind:
            case "attack" | "transfer":
                card = Card.parse(event.data["card"])
                self._played(player, card)
                self.table.append([card, None])
            case "defend":
                card = Card.parse(event.data["card"])
                self._played(player, card)
                self.table[event.data["attack_index"]][1] = card
            case "trump_swap":
                assert player is not None
                self.known[player].discard(Card.parse(event.data["card"]))
                self.known[player].add(Card.parse(event.data["took"]))
                self.face_up = Card.parse(event.data["card"])
            case "bout_taken":
                assert player is not None
                self.known[player] |= self.table_cards()
                self.table = []
                self.first_bout = False
            case "bout_beaten":
                self.discard |= self.table_cards()
                self.table = []
                self.first_bout = False
            case "draw":
                assert player is not None
                self.talon_count -= event.data["count"]
                # The face-up trump card is drawn last, by whoever empties the talon.
                if self.talon_count == 0 and self.face_up is not None:
                    self.known[player].add(self.face_up)
                    self.face_up = None

    def _played(self, player: int | None, card: Card) -> None:
        if player is not None:
            self.known[player].discard(card)
