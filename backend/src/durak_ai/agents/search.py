from __future__ import annotations

import random
import time
from dataclasses import dataclass

from durak_engine import (
    Action,
    Card,
    Game,
    GameState,
    Phase,
    PlayerView,
    Rank,
    Suit,
    SwapTrump,
    TablePair,
)

from ..agent import Agent, may_wait
from ..arena import next_move
from ..config import outcome_reward
from .heuristic import HeuristicAgent, HeuristicParams

Deal = tuple[list[list[Card]], list[Card]]  # every hand, then the talon


@dataclass(frozen=True)
class SearchParams:
    # Determinizations per decision. Every candidate is played out once per deal.
    samples: int = 16
    # Optional wall-clock budget per decision; sampling stops once it is spent.
    time_limit: float | None = None
    max_rollout_steps: int = 1000
    rollout: HeuristicParams = HeuristicParams()


class SearchAgent(Agent):
    """Determinized Monte Carlo ("perfect information Monte Carlo").

    For each sample, deal the cards this seat can't see into opponents' hands and
    the talon, consistent with everything the tracker knows. Then play every
    candidate move out to the end with heuristic players and keep the move with
    the best total result. The same deals are used for every candidate, so the
    comparison isn't swamped by luck of the deal.
    """

    name = "search"

    def __init__(self, params: SearchParams | None = None, seed: int | None = None) -> None:
        self.params = params or SearchParams()
        self.rng = random.Random(seed)
        self.fallback = HeuristicAgent(self.params.rollout)

    def reset(self, seat, config, view) -> None:
        super().reset(seat, config, view)
        self.fallback.reset(seat, config, view)

    def observe(self, view, events) -> None:
        super().observe(view, events)
        self.fallback.observe(view, events)

    def act(self, view: PlayerView, legal: list[Action]) -> Action | None:
        if SwapTrump() in legal:
            return SwapTrump()
        candidates: list[Action | None] = list(legal)
        if may_wait(view, legal):
            candidates.append(None)
        if len(candidates) == 1:
            return candidates[0]

        # Ties go to the heuristic's choice rather than to list order.
        preferred = self.fallback.act(view, legal)
        totals = [1e-6 if c == preferred else 0.0 for c in candidates]
        deadline = time.monotonic() + self.params.time_limit if self.params.time_limit else None
        for _ in range(self.params.samples):
            deal = self._sample_deal(view)
            if deal is None:
                return preferred
            for i, candidate in enumerate(candidates):
                totals[i] += self._rollout(view, deal, candidate)
            if deadline is not None and time.monotonic() > deadline:
                break
        return candidates[max(range(len(candidates)), key=totals.__getitem__)]

    # --------------------------------------------------------- determinizing

    def _sample_deal(self, view: PlayerView) -> Deal | None:
        t = self.tracker
        pool = list(t.unseen())
        self.rng.shuffle(pool)
        hands: list[list[Card]] = []
        for player in range(self.config.num_players):
            if player == self.seat:
                hands.append(list(view.hand))
                continue
            count = t.unknown_count(player)
            if count < 0 or count > len(pool):
                return None
            hands.append(list(t.known[player]) + pool[:count])
            pool = pool[count:]
        face_up = [t.face_up] if t.face_up is not None else []
        if len(face_up) + len(pool) != view.talon_count:
            return None  # tracker out of step with the view; don't guess
        return hands, face_up + pool

    def _build(self, view: PlayerView, deal: Deal) -> Game:
        hands, talon = deal
        trump = Suit(view.trump_suit)
        state = GameState(
            config=self.config,
            hands=[list(h) for h in hands],
            talon=list(talon),
            # Once the talon is empty only the suit matters.
            trump_card=talon[0] if talon else Card(Rank.ACE, trump),
            attacker=view.attacker,
            defender=view.defender,
            bout_limit=view.bout_limit,
            table=[TablePair(a, d) for a, d in view.table],
            discard=list(self.tracker.discard),
            phase=Phase(view.phase),
            passed=set(view.passed),
            out_order=list(view.out_order),
            durak=view.durak,
            winner=view.winner,
            # The view doesn't say who ran out first this bout; seat order will do.
            emptied=[p for p, n in enumerate(view.hand_counts) if n == 0 and p not in view.out_order],
            is_first_bout=self.tracker.first_bout,
        )
        return Game(state)

    # --------------------------------------------------------------- rollout

    def _rollout(self, view: PlayerView, deal: Deal, candidate: Action | None) -> float:
        game = self._build(view, deal)
        players = self.config.num_players
        # Heuristic players keep no memory between moves, so they don't need
        # observe() calls, which keeps rollouts cheap.
        agents = [HeuristicAgent(self.params.rollout) for _ in range(players)]
        for seat, agent in enumerate(agents):
            agent.reset(seat, self.config, game.view(seat))

        if candidate is None:
            game.apply(*next_move(game, agents, self.rng, skip=self.seat))
        else:
            game.apply(self.seat, candidate)
        for _ in range(self.params.max_rollout_steps):
            if game.finished:
                return outcome_reward(game.state.winner, self.seat, players)
            game.apply(*next_move(game, agents, self.rng))
        return 0.0
