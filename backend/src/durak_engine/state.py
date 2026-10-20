from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .cards import Card, Suit
from .config import GameConfig


class Phase(Enum):
    ATTACKING = "attacking"
    DEFENDER_TAKING = "defender_taking"
    FINISHED = "finished"


@dataclass
class TablePair:
    attack: Card
    defense: Card | None = None


@dataclass
class GameState:
    """Plain game data. All rule logic lives in `Game`; this stays cheap to copy."""

    config: GameConfig
    hands: list[list[Card]]
    talon: list[Card]  # drawn from the end; talon[0] is the face-up trump card
    trump_card: Card
    attacker: int
    defender: int
    bout_limit: int
    table: list[TablePair] = field(default_factory=list)
    discard: list[Card] = field(default_factory=list)
    phase: Phase = Phase.ATTACKING
    passed: set[int] = field(default_factory=set)
    out_order: list[int] = field(default_factory=list)
    durak: int | None = None
    winner: int | None = None  # only set with `first_out_wins`
    emptied: list[int] = field(default_factory=list)  # ran out of cards this bout, in order
    is_first_bout: bool = True

    @property
    def trump_suit(self) -> Suit:
        return self.trump_card.suit

    @property
    def num_players(self) -> int:
        return len(self.hands)
