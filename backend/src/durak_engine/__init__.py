"""Pure-Python Durak rules engine with no web dependencies."""

from .actions import (
    Action,
    Attack,
    Defend,
    Pass,
    SwapTrump,
    Take,
    Transfer,
    action_from_dict,
    action_to_dict,
)
from .cards import Card, Rank, Suit, lowest_rank, make_deck
from .config import GameConfig
from .errors import IllegalAction
from .game import Game
from .state import GameState, Phase, TablePair
from .views import Event, PlayerView

__all__ = [
    "Action",
    "Attack",
    "Card",
    "Defend",
    "Event",
    "Game",
    "GameConfig",
    "GameState",
    "IllegalAction",
    "Pass",
    "Phase",
    "PlayerView",
    "Rank",
    "Suit",
    "SwapTrump",
    "TablePair",
    "Take",
    "Transfer",
    "action_from_dict",
    "action_to_dict",
    "lowest_rank",
    "make_deck",
]
