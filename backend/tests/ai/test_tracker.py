import random

import pytest

from durak_ai import Agent, RandomAgent, ai_config, play_game
from durak_engine import Game


class CheckedRandom(RandomAgent):
    """A random agent that checks its tracker against the true game after every move."""

    game: Game

    def observe(self, view, events):
        super().observe(view, events)
        s = self.game.state
        t = self.tracker
        assert t.discard == set(s.discard)
        assert t.table_cards() == {c for p in s.table for c in (p.attack, p.defense) if c}
        for player, cards in enumerate(t.known):
            assert cards <= set(s.hands[player]), f"seat {player} known cards not in hand"
        hidden = set(s.talon[1:] if s.talon else [])
        for player, hand in enumerate(s.hands):
            if player != self.seat:
                hidden |= set(hand) - t.known[player]
        assert t.unseen() == hidden
        for player in range(s.num_players):
            assert t.unknown_count(player) >= 0


@pytest.mark.parametrize("num_players", [2, 3, 4, 5, 6])
def test_tracker_matches_true_state(num_players, monkeypatch):
    agents = [CheckedRandom(seed=i) for i in range(num_players)]

    # Hand every agent the live game so it can check itself. Real agents never see it.
    real_new = Game.new

    def new(config, seed=None):
        game = real_new(config, seed)
        for agent in agents:
            agent.game = game
        return game

    monkeypatch.setattr(Game, "new", staticmethod(new))
    for seed in range(20):
        play_game(agents, seed=seed)


def test_known_cards_after_take():
    """Cards a defender picks up become known to everyone else."""
    rng = random.Random(0)
    found = False
    for seed in range(20):
        agents = [RandomAgent(seed=rng.random()) for _ in range(3)]
        play_game(agents, seed=seed)
        if any(agent.tracker.known[p] for agent in agents for p in range(3) if p != agent.seat):
            found = True
            break
    assert found


def test_reset_rejects_other_configs():
    from durak_engine import GameConfig

    game = Game.new(GameConfig(num_players=2, deck_size=36), seed=1)
    agent: Agent = RandomAgent()
    with pytest.raises(ValueError):
        agent.reset(0, game.state.config, game.view(0))
    game = Game.new(ai_config(2), seed=1)
    agent.reset(0, game.state.config, game.view(0))
