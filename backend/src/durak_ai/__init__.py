"""AI players for the Durak engine. Only `durak_ai.nn` needs PyTorch."""

from .agent import Agent, may_wait
from .agents import HeuristicAgent, HeuristicParams, RandomAgent, SearchAgent, SearchParams
from .arena import AgentError, GameResult, MatchStats, Tally, play_game, run_match
from .config import AI_PLAYER_COUNTS, ai_config, check_ai_config, outcome_reward
from .tracker import CardTracker

__all__ = [
    "AI_PLAYER_COUNTS",
    "Agent",
    "AgentError",
    "CardTracker",
    "GameResult",
    "HeuristicAgent",
    "HeuristicParams",
    "MatchStats",
    "RandomAgent",
    "SearchAgent",
    "SearchParams",
    "Tally",
    "ai_config",
    "check_ai_config",
    "may_wait",
    "outcome_reward",
    "play_game",
    "run_match",
]
