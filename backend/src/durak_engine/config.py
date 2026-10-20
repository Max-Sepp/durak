from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GameConfig:
    num_players: int = 2
    deck_size: int = 36
    # Perevodnoy: the defender may pass the attack on with a card of the same rank.
    transfer_enabled: bool = True
    # Holder of the lowest trump (2 or 6) may swap it for the face-up trump card.
    trump_swap_enabled: bool = True
    # Every non-defender may throw in; when off, only the main attacker may.
    all_players_throw_in: bool = True
    # Attackers may keep adding cards after the defender declares "take".
    throw_in_after_take: bool = True
    # The first player to get rid of all their cards wins and the game ends there.
    first_out_wins: bool = True
    hand_size: int = 6
    max_bout_cards: int = 6
    first_bout_limit: int = 5

    def __post_init__(self) -> None:
        if not 2 <= self.num_players <= 6:
            raise ValueError("num_players must be between 2 and 6")
        if self.deck_size not in (36, 52):
            raise ValueError("deck_size must be 36 or 52")
        if self.num_players * self.hand_size > self.deck_size:
            raise ValueError("not enough cards to deal every player a full hand")
        if not 1 <= self.first_bout_limit <= self.max_bout_cards:
            raise ValueError("first_bout_limit must be between 1 and max_bout_cards")
