import itertools
import random

import pytest

from durak_engine import Game, GameConfig, Phase

TABLES = list(itertools.product(range(2, 7), (36, 52)))
RULES = ("transfer_enabled", "trump_swap_enabled", "all_players_throw_in", "throw_in_after_take")


def total_cards(game: Game) -> int:
    s = game.state
    return (
        sum(len(h) for h in s.hands)
        + len(s.talon)
        + len(s.discard)
        + sum(1 + (p.defense is not None) for p in s.table)
    )


@pytest.mark.parametrize(("num_players", "deck_size"), TABLES, ids=lambda v: str(v))
def test_random_playouts_terminate_and_conserve_cards(num_players: int, deck_size: int):
    for seed in range(50):
        rng = random.Random(seed)
        # Cover every on/off combination of the optional rules across seeds.
        flags = dict(zip(RULES, (bool(seed >> i & 1) for i in range(len(RULES)))))
        config = GameConfig(num_players=num_players, deck_size=deck_size, **flags)
        game = Game.new(config, seed=seed)
        for _ in range(5000):
            if game.finished:
                break
            actors = sorted(game.current_actors())
            assert actors, "game stalled with nobody able to act"
            player = rng.choice(actors)
            game.apply(player, rng.choice(game.legal_actions(player)))
            assert total_cards(game) == deck_size
            s = game.state
            assert s.attacker not in s.out_order or game.finished
            assert s.attacker != s.defender or game.finished
            assert sum(p.defense is None for p in s.table) <= len(s.hands[s.defender]) or s.phase is Phase.DEFENDER_TAKING
        assert game.finished, f"seed {seed} ({flags}) did not finish"
        assert len(game.state.out_order) >= num_players - 1
