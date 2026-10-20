import random

import pytest

from durak_ai import HeuristicAgent, RandomAgent, SearchAgent, SearchParams, ai_config, play_game
from durak_engine import Game

FAST = SearchParams(samples=2)


@pytest.mark.parametrize("num_players", [2, 3, 4, 5, 6])
def test_determinized_games_match_the_real_one(num_players):
    """A rebuilt game must agree with the real one on everything the seat can see,
    hold the same cards overall, and put known cards where they really are."""
    for seed in range(5):
        game = Game.new(ai_config(num_players), seed=seed)
        searchers = [SearchAgent(FAST, seed=seed) for _ in range(num_players)]
        for seat, agent in enumerate(searchers):
            agent.reset(seat, game.state.config, game.view(seat))
        rng = random.Random(seed)
        while not game.finished:
            s = game.state
            for seat, agent in enumerate(searchers):
                view = game.view(seat)
                deal = agent._sample_deal(view)
                assert deal is not None
                built = agent._build(view, deal)
                b = built.state
                assert built.view(seat) == view
                assert set(built.legal_actions(seat)) == set(game.legal_actions(seat))
                assert [len(h) for h in b.hands] == [len(h) for h in s.hands]
                hidden = {c for h in s.hands for c in h} | set(s.talon)
                assert {c for h in b.hands for c in h} | set(b.talon) == hidden
                for player, known in enumerate(agent.tracker.known):
                    assert known <= set(b.hands[player])
            actors = sorted(game.current_actors())
            player = rng.choice(actors)
            events = game.apply(player, rng.choice(game.legal_actions(player)))
            for seat, agent in enumerate(searchers):
                agent.observe(game.view(seat), events)


@pytest.mark.parametrize("num_players", [2, 3, 4, 5, 6])
def test_search_games_finish(num_players):
    agents = [SearchAgent(FAST, seed=0)] + [HeuristicAgent() for _ in range(num_players - 1)]
    for seed in range(3):
        assert not play_game(agents, seed=seed).truncated


def test_search_beats_random():
    wins = 0
    for seed in range(20):
        result = play_game([SearchAgent(FAST, seed=seed), RandomAgent(seed=seed)], seed=seed)
        wins += result.durak == 1
    assert wins >= 18
