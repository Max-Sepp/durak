from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .cards import Card


@dataclass(frozen=True)
class Attack:
    """Open a bout or throw in a card whose rank is already on the table."""

    card: Card


@dataclass(frozen=True)
class Defend:
    attack_index: int
    card: Card


@dataclass(frozen=True)
class Transfer:
    """Perevodnoy: pass the attack on to the next player with a card of the same rank."""

    card: Card


@dataclass(frozen=True)
class Take:
    pass


@dataclass(frozen=True)
class Pass:
    """An attacker declares they are done throwing in for this bout ("bito")."""


@dataclass(frozen=True)
class SwapTrump:
    """Swap the lowest trump in hand for the face-up trump card under the deck."""


Action = Attack | Defend | Transfer | Take | Pass | SwapTrump


def action_to_dict(action: Action) -> dict[str, Any]:
    match action:
        case Attack(card):
            return {"kind": "attack", "card": str(card)}
        case Defend(index, card):
            return {"kind": "defend", "attack_index": index, "card": str(card)}
        case Transfer(card):
            return {"kind": "transfer", "card": str(card)}
        case Take():
            return {"kind": "take"}
        case Pass():
            return {"kind": "pass"}
        case SwapTrump():
            return {"kind": "swap_trump"}
    raise TypeError(f"unknown action: {action!r}")


def action_from_dict(data: dict[str, Any]) -> Action:
    kind = data.get("kind")
    match kind:
        case "attack":
            return Attack(Card.parse(data["card"]))
        case "defend":
            return Defend(int(data["attack_index"]), Card.parse(data["card"]))
        case "transfer":
            return Transfer(Card.parse(data["card"]))
        case "take":
            return Take()
        case "pass":
            return Pass()
        case "swap_trump":
            return SwapTrump()
    raise ValueError(f"unknown action kind: {kind!r}")
