from __future__ import annotations

import random

from durak_engine import Action, PlayerView

from ..agent import Agent


class RandomAgent(Agent):
    """Uniform over legal actions. A baseline and a fuzzing partner."""

    name = "random"

    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)

    def act(self, view: PlayerView, legal: list[Action]) -> Action | None:
        return self.rng.choice(legal)
