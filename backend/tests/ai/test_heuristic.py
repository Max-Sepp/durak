import pytest

from durak_ai import HeuristicAgent, RandomAgent, ai_config, play_game, run_match
from durak_engine import Attack, Card, Defend, Game, GameState, Pass, Phase, SwapTrump, Take, TablePair, Transfer


def c(text: str) -> Card:
    return Card.parse(text)


def decide(
    hands: list[list[str]],
    seat: int,
    table: list[tuple[str, str | None]] = (),
    talon: list[str] = ("3S", "4D", "5D", "6D", "7D", "8D", "9D", "10D", "JD", "QD"),
    attacker: int = 0,
    phase: Phase = Phase.ATTACKING,
):
    """Ask a fresh HeuristicAgent at `seat` what it would play in a hand-built position."""
    talon_cards = [c(x) for x in talon]
    state = GameState(
        config=ai_config(len(hands)),
        hands=[[c(x) for x in h] for h in hands],
        talon=talon_cards,
        trump_card=talon_cards[0] if talon_cards else c("3S"),
        attacker=attacker,
        defender=(attacker + 1) % len(hands),
        bout_limit=6,
        table=[TablePair(c(a), c(d) if d else None) for a, d in table],
        phase=phase,
        is_first_bout=False,
    )
    game = Game(state)
    agent = HeuristicAgent()
    agent.reset(seat, state.config, game.view(seat))
    return agent.act(game.view(seat), game.legal_actions(seat))


def test_swaps_trump_whenever_possible():
    assert decide([["5H", "6H"], ["2S", "4H"]], seat=1) == SwapTrump()


def test_opens_with_cheapest_card_preferring_pairs():
    assert decide([["4H", "9C", "AS"], ["5H"]], seat=0) == Attack(c("4H"))
    assert decide([["4H", "5C", "5D"], ["5H"]], seat=0) == Attack(c("5C"))


def test_defends_with_cheapest_beating_card():
    action = decide([["KH"], ["7C", "8C", "AC", "4S"]], seat=1, table=[("6C", None)])
    assert action == Defend(0, c("7C"))


def test_spends_a_high_trump_only_late():
    hands = [["KH"], ["5C", "AS"]]
    long_talon = ["3S"] + [f"{r}{s}" for s in "DH" for r in ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q"]]
    assert decide(hands, seat=1, table=[("6C", None)], talon=long_talon) == Take()
    assert decide(hands, seat=1, table=[("6C", None)], talon=["3S"]) == Defend(0, c("AS"))


def test_takes_when_it_cannot_beat():
    assert decide([["KH"], ["7C"]], seat=1, table=[("8C", None)]) == Take()


def test_transfers_with_a_cheap_card():
    action = decide([["KH"], ["6D", "8C", "AC"], ["9H", "10H", "JH"]], seat=1, table=[("6C", None)])
    assert action == Transfer(c("6D"))


def test_throw_in_rules():
    # Cheap matching non-trump: throw it in. Trump of the same rank: never.
    hands = [["5H", "5S", "KC"], ["9C", "AD"], ["7H"]]
    assert decide(hands, seat=0, table=[("5C", "9C")]) == Attack(c("5H"))
    hands = [["5S", "KC"], ["9C", "AD"], ["7H"]]
    assert decide(hands, seat=0, table=[("5C", "9C")]) == Pass()
    # While the defender is still deciding, wait rather than pass.
    assert decide(hands, seat=0, table=[("5C", None)]) is None
    # Dump cheap cards on a defender who is taking.
    hands = [["7H", "KC"], ["9C", "AD"], ["7S"]]
    assert decide(hands, seat=0, table=[("7C", None)], phase=Phase.DEFENDER_TAKING) == Attack(c("7H"))


@pytest.mark.parametrize("num_players", [2, 3, 4, 5, 6])
def test_heuristic_games_finish(num_players):
    for seed in range(20):
        agents = [HeuristicAgent() if i % 2 == 0 else RandomAgent(seed=i) for i in range(num_players)]
        assert not play_game(agents, seed=seed).truncated
        assert not play_game([HeuristicAgent() for _ in range(num_players)], seed=seed).truncated


def test_heuristic_beats_random():
    stats = run_match([HeuristicAgent, RandomAgent], games=200, seed=0)
    for n, tally in stats.by_players.items():
        _, hi = tally.interval()
        assert hi < 1 / n, f"{n} players: durak rate {tally.durak_rate:.3f} not below {1 / n:.3f}"
