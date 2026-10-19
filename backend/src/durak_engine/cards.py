from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, IntEnum


class Suit(Enum):
    CLUBS = "C"
    DIAMONDS = "D"
    HEARTS = "H"
    SPADES = "S"


class Rank(IntEnum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14

    @property
    def symbol(self) -> str:
        return _RANK_SYMBOLS.get(self, str(self.value))

    @classmethod
    def from_symbol(cls, symbol: str) -> Rank:
        for rank, sym in _RANK_SYMBOLS.items():
            if sym == symbol:
                return rank
        return cls(int(symbol))


_RANK_SYMBOLS = {Rank.JACK: "J", Rank.QUEEN: "Q", Rank.KING: "K", Rank.ACE: "A"}


@dataclass(frozen=True, order=True)
class Card:
    rank: Rank
    suit: Suit

    def __str__(self) -> str:
        return f"{self.rank.symbol}{self.suit.value}"

    @classmethod
    def parse(cls, text: str) -> Card:
        """Parse the compact form, e.g. "10H" or "AS"."""
        if len(text) < 2:
            raise ValueError(f"invalid card: {text!r}")
        try:
            return cls(Rank.from_symbol(text[:-1]), Suit(text[-1]))
        except ValueError:
            raise ValueError(f"invalid card: {text!r}") from None

    def beats(self, other: Card, trump: Suit) -> bool:
        if self.suit == other.suit:
            return self.rank > other.rank
        return self.suit == trump


def lowest_rank(deck_size: int) -> Rank:
    if deck_size not in (36, 52):
        raise ValueError("deck size must be 36 or 52")
    return Rank.SIX if deck_size == 36 else Rank.TWO


def make_deck(size: int, rng: random.Random | None = None) -> list[Card]:
    lowest = lowest_rank(size)
    deck = [Card(rank, suit) for suit in Suit for rank in Rank if rank >= lowest]
    if rng is not None:
        rng.shuffle(deck)
    return deck
