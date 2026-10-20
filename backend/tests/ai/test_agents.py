import pytest

from durak_ai import AgentError, RandomAgent, play_game, run_match
from durak_ai.__main__ import main
from durak_engine import Attack


@pytest.mark.parametrize("num_players", [2, 3, 4, 5, 6])
def test_random_agents_finish_games(num_players):
    for seed in range(30):
        result = play_game([RandomAgent(seed=seed * 10 + i) for i in range(num_players)], seed=seed)
        assert result.out_order and not result.truncated
        assert result.winner is not None and result.out_order == [result.winner]


def test_play_game_is_reproducible():
    def run():
        return play_game([RandomAgent(seed=i) for i in range(4)], seed=7)

    assert run() == run()


class Waiter(RandomAgent):
    def act(self, view, legal):
        return None


class Cheater(RandomAgent):
    def act(self, view, legal):
        return Attack(view.hand[0]) if view.attacker == self.seat else super().act(view, legal)


def test_contract_violations_raise():
    with pytest.raises(AgentError, match="waited"):
        play_game([Waiter(), Waiter()], seed=1)
    with pytest.raises(AgentError, match="illegal"):
        for seed in range(20):
            play_game([Cheater(seed=0), Cheater(seed=1)], seed=seed)


def test_run_match_rotates_seats_and_counts():
    stats = run_match([RandomAgent], games=50, seed=3, players=[2, 3, 6])
    assert sorted(stats.by_players) == [2, 3, 6]
    assert stats.total.games == 50
    for tally in stats.by_players.values():
        lo, hi = tally.interval()
        assert 0 <= lo <= tally.win_rate <= hi <= 1


def test_cli_runs(capsys):
    main(["--agents", "random", "--games", "10", "--players", "2-3", "--seed", "1"])
    assert "subject: random" in capsys.readouterr().out
