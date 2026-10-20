"""Play agents against each other. The command-line entry point is `durak_ai.__main__`."""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from durak_engine import Action, Game, Pass

from .agent import Agent
from .config import AI_PLAYER_COUNTS, ai_config


class AgentError(Exception):
    """An agent broke the `Agent` contract (illegal move, or waiting when it can't)."""


@dataclass(frozen=True)
class GameResult:
    durak: int | None
    out_order: list[int]
    steps: int
    agents: list[str]
    # Hit max_steps. Durak has no repetition rule, so endgames can cycle forever
    # (the same cards passed round and taken); these count as draws.
    truncated: bool = False


def play_game(
    agents: Sequence[Agent],
    seed: int | None = None,
    max_steps: int = 2_000,
) -> GameResult:
    rng = random.Random(seed)
    config = ai_config(len(agents))
    game = Game.new(config, seed=rng.getrandbits(64))
    for seat, agent in enumerate(agents):
        agent.reset(seat, config, game.view(seat))

    steps = 0
    while not game.finished and steps < max_steps:
        player, action = next_move(game, agents, rng)
        events = game.apply(player, action)
        for seat, agent in enumerate(agents):
            agent.observe(game.view(seat), events)
        steps += 1

    s = game.state
    return GameResult(
        durak=s.durak,
        out_order=list(s.out_order),
        steps=steps,
        agents=[a.name for a in agents],
        truncated=not game.finished,
    )


def next_move(
    game: Game, agents: Sequence[Agent], rng: random.Random, skip: int | None = None
) -> tuple[int, Action]:
    """Ask the seats that can act, in random order, until one moves. `skip` leaves
    one seat out, as if it had chosen to wait (used by search rollouts)."""
    actors = sorted(p for p in game.current_actors() if p != skip)
    rng.shuffle(actors)
    for player in actors:
        legal = game.legal_actions(player)
        action = agents[player].act(game.view(player), legal)
        if action is None and Pass() in legal:
            action = Pass()
        if action is None:
            continue
        if action not in legal:
            raise AgentError(f"{agents[player].name} (seat {player}) played illegal {action!r}")
        return player, action
    raise AgentError(f"every actor waited: seats {sorted(actors)}")


# ------------------------------------------------------------------- matches


@dataclass
class Tally:
    games: int = 0
    durak: int = 0
    draws: int = 0
    truncated: int = 0

    @property
    def durak_rate(self) -> float:
        return self.durak / self.games if self.games else 0.0

    def interval(self, z: float = 1.96) -> tuple[float, float]:
        """Wilson score interval for the durak rate."""
        if not self.games:
            return 0.0, 1.0
        n, p = self.games, self.durak_rate
        centre = (p + z * z / (2 * n)) / (1 + z * z / n)
        spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
        return centre - spread, centre + spread


@dataclass
class MatchStats:
    """How often the subject (the first agent) ends up durak, per player count."""

    by_players: dict[int, Tally] = field(default_factory=dict)

    @property
    def total(self) -> Tally:
        out = Tally()
        for t in self.by_players.values():
            out.games += t.games
            out.durak += t.durak
            out.draws += t.draws
            out.truncated += t.truncated
        return out

    def record(self, num_players: int, subject_seat: int, result: GameResult) -> None:
        tally = self.by_players.setdefault(num_players, Tally())
        tally.games += 1
        if result.durak is None:
            tally.draws += 1
            tally.truncated += result.truncated
        elif result.durak == subject_seat:
            tally.durak += 1


AgentFactory = Callable[[], Agent]


def run_match(
    factories: Sequence[AgentFactory],
    games: int,
    seed: int | None = None,
    players: Sequence[int] = AI_PLAYER_COUNTS,
) -> MatchStats:
    """Play `games` games, cycling through player counts and rotating the subject's seat."""
    rng = random.Random(seed)
    subject, others = factories[0], list(factories[1:]) or [factories[0]]
    stats = MatchStats()
    for i in range(games):
        n = players[i % len(players)]
        subject_seat = (i // len(players)) % n
        opponents = iter(others[j % len(others)] for j in range(n - 1))
        agents = [subject() if seat == subject_seat else next(opponents)() for seat in range(n)]
        stats.record(n, subject_seat, play_game(agents, seed=rng.getrandbits(64)))
    return stats
