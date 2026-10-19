from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .cards import Card


@dataclass(frozen=True)
class Event:
    kind: str
    player: int | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "player": self.player, **self.data}


@dataclass(frozen=True)
class PlayerView:
    """What one seat is allowed to see. Other players' hands are reduced to counts."""

    you: int
    hand: list[Card]
    hand_counts: list[int]
    talon_count: int
    trump_card: Card | None  # None once the trump card itself has been drawn
    trump_suit: str
    table: list[tuple[Card, Card | None]]
    attacker: int
    defender: int
    phase: str
    passed: list[int]
    out_order: list[int]
    durak: int | None
    discard_count: int
    bout_limit: int
    transfer_enabled: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "you": self.you,
            "hand": [str(c) for c in self.hand],
            "hand_counts": self.hand_counts,
            "talon_count": self.talon_count,
            "trump_card": str(self.trump_card) if self.trump_card else None,
            "trump_suit": self.trump_suit,
            "table": [
                {"attack": str(a), "defense": str(d) if d else None} for a, d in self.table
            ],
            "attacker": self.attacker,
            "defender": self.defender,
            "phase": self.phase,
            "passed": self.passed,
            "out_order": self.out_order,
            "durak": self.durak,
            "discard_count": self.discard_count,
            "bout_limit": self.bout_limit,
            "transfer_enabled": self.transfer_enabled,
        }
