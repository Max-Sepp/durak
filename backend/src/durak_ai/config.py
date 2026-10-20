from __future__ import annotations

from durak_engine import GameConfig

AI_DECK_SIZE = 52
AI_PLAYER_COUNTS = (2, 3, 4, 5, 6)


def ai_config(num_players: int) -> GameConfig:
    """The one game the AIs are built for: 52 cards with every optional rule on."""
    return GameConfig(
        num_players=num_players,
        deck_size=AI_DECK_SIZE,
        transfer_enabled=True,
        trump_swap_enabled=True,
        all_players_throw_in=True,
        throw_in_after_take=True,
    )


def check_ai_config(config: GameConfig) -> None:
    if config != ai_config(config.num_players):
        raise ValueError(f"AIs only play 52 cards with all rules on, got {config!r}")


def outcome_reward(durak: int | None, seat: int, num_players: int) -> float:
    """Zero-sum game result for `seat`: the durak gets -1, everyone else shares +1."""
    if durak is None:
        return 0.0
    return -1.0 if durak == seat else 1.0 / (num_players - 1)
