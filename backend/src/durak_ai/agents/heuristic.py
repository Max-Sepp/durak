from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from durak_engine import (
    Action,
    Attack,
    Card,
    Defend,
    Pass,
    Phase,
    PlayerView,
    Suit,
    SwapTrump,
    Take,
    Transfer,
)

from ..agent import Agent


@dataclass(frozen=True)
class HeuristicParams:
    """Tunable thresholds, in units of card cost (2 = 0 ... A = 12, trumps +13)."""

    trump_bonus: float = 13.0
    # Opening: discount per extra card of the same rank held, so pairs get led.
    pair_bonus: float = 3.0
    # Throw in non-trumps costing at most this much, rising as the talon empties.
    throw_in_max: float = 4.0
    throw_in_late_bonus: float = 8.0
    # Dump non-trumps up to this cost on a defender who has already taken.
    dump_max: float = 7.0
    # Defend while the cards spent cost no more than the price of taking:
    # take_base + take_per_card * cards on the table, scaled up as the talon empties.
    take_base: float = 6.0
    take_per_card: float = 4.0
    take_late_scale: float = 3.0


class HeuristicAgent(Agent):
    """Rule-based player: keep trumps and high cards, shed low cards, take when
    defending would cost more than the cards on the table are worth."""

    name = "heuristic"

    def __init__(self, params: HeuristicParams | None = None) -> None:
        self.params = params or HeuristicParams()

    def reset(self, seat, config, view) -> None:
        super().reset(seat, config, view)
        self.initial_talon = max(config.deck_size - config.num_players * config.hand_size, 1)

    # ------------------------------------------------------------- decisions

    def act(self, view: PlayerView, legal: list[Action]) -> Action | None:
        if SwapTrump() in legal:
            return SwapTrump()
        if view.you == view.defender:
            return self._defend(view, legal)
        attacks = [a.card for a in legal if isinstance(a, Attack)]
        if not view.table:
            return Attack(self._opening_card(view, attacks)) if attacks else None
        return self._throw_in(view, attacks, legal)

    def _opening_card(self, view: PlayerView, cards: list[Card]) -> Card:
        counts = Counter(c.rank for c in view.hand)
        return min(cards, key=lambda c: self.cost(c, view) - self.params.pair_bonus * (counts[c.rank] - 1))

    def _throw_in(self, view: PlayerView, cards: list[Card], legal: list[Action]) -> Action | None:
        p = self.params
        trump = Suit(view.trump_suit)
        talon_empty = view.talon_count == 0
        if view.phase == Phase.DEFENDER_TAKING.value:
            limit = p.dump_max
        else:
            limit = p.throw_in_max + p.throw_in_late_bonus * (1 - self._talon_fraction(view))
        # Once the talon is empty, every card shed is a step towards getting out.
        # Trumps are never thrown in: a defender who takes them gets stronger.
        candidates = [
            c for c in cards
            if c.suit != trump and (talon_empty or self.cost(c, view) <= limit)
        ]
        if candidates:
            return Attack(min(candidates, key=lambda c: self.cost(c, view)))
        return Pass() if Pass() in legal else None

    def _defend(self, view: PlayerView, legal: list[Action]) -> Action | None:
        if all(d is not None for _, d in view.table):
            return None
        plan = self._defence_plan(view)
        defend_cost = sum(self.cost(c, view) for _, c in plan) if plan is not None else float("inf")

        transfers = [a.card for a in legal if isinstance(a, Transfer)]
        if transfers:
            card = min(transfers, key=lambda c: self.cost(c, view))
            if self.cost(card, view) <= min(defend_cost, self._take_cost(view)):
                return Transfer(card)

        if plan is None or defend_cost > self._take_cost(view):
            return Take()
        index, card = plan[0]
        return Defend(index, card)

    def _defence_plan(self, view: PlayerView) -> list[tuple[int, Card]] | None:
        """Cheapest cards that beat every open attack, most expensive attack first.
        None when some attack can't be beaten."""
        trump = Suit(view.trump_suit)
        open_attacks = [(i, a) for i, (a, d) in enumerate(view.table) if d is None]
        open_attacks.sort(key=lambda ia: self.cost(ia[1], view), reverse=True)
        available = sorted(view.hand, key=lambda c: self.cost(c, view))
        plan: list[tuple[int, Card]] = []
        for index, attack in open_attacks:
            beater = next((c for c in available if c.beats(attack, trump)), None)
            if beater is None:
                return None
            available.remove(beater)
            plan.append((index, beater))
        return plan

    # --------------------------------------------------------------- scoring

    def cost(self, card: Card, view: PlayerView) -> float:
        value = float(card.rank - 2)
        if card.suit.value == view.trump_suit:
            value += self.params.trump_bonus
        return value

    def _talon_fraction(self, view: PlayerView) -> float:
        return min(view.talon_count / self.initial_talon, 1.0)

    def _take_cost(self, view: PlayerView) -> float:
        p = self.params
        cards = sum(1 + (d is not None) for _, d in view.table)
        late = 1 + p.take_late_scale * (1 - self._talon_fraction(view))
        return (p.take_base + p.take_per_card * cards) * late
