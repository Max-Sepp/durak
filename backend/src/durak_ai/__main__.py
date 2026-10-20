"""Play agents against each other.

    uv run python -m durak_ai --agents random,random --games 2000 --players 2-6

The first agent is the subject; the other seats cycle through the remaining
agents (or the subject itself, if only one is given).
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from .agents import HeuristicAgent, RandomAgent, SearchAgent
from .arena import AgentFactory, run_match

AGENTS: dict[str, AgentFactory] = {
    "heuristic": HeuristicAgent,
    "random": RandomAgent,
    "search": SearchAgent,
}


def _parse_players(text: str) -> list[int]:
    if "-" in text:
        lo, hi = (int(x) for x in text.split("-"))
        return list(range(lo, hi + 1))
    return [int(x) for x in text.split(",")]


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--agents", default="random", help=f"comma-separated, from {sorted(AGENTS)}")
    parser.add_argument("--games", type=int, default=1000)
    parser.add_argument("--players", default="2-6", help="e.g. 2-6 or 2,4")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args(argv)

    names = args.agents.split(",")
    unknown = [n for n in names if n not in AGENTS]
    if unknown:
        parser.error(f"unknown agents {unknown}; choose from {sorted(AGENTS)}")
    stats = run_match([AGENTS[n] for n in names], args.games, args.seed, _parse_players(args.players))

    print(f"subject: {names[0]}  opponents: {','.join(names[1:]) or names[0]}")
    print(f"{'players':>7}  {'games':>6}  {'wins':>6}  {'baseline':>8}  {'95% interval':<14}  {'draws':>5}  {'cut':>4}")
    rows = [(str(n), t, 1 / n) for n, t in sorted(stats.by_players.items())]
    rows.append(("all", stats.total, None))
    for label, t, baseline in rows:
        lo, hi = t.interval()
        base = f"{baseline:8.3f}" if baseline is not None else " " * 8
        print(
            f"{label:>7}  {t.games:>6}  {t.win_rate:6.3f}  {base}  [{lo:.3f}, {hi:.3f}]  "
            f"{t.draws:>5}  {t.truncated:>4}"
        )


if __name__ == "__main__":
    main()
