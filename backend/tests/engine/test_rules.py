import pytest

from durak_engine import (
    Attack,
    Card,
    Defend,
    Game,
    GameConfig,
    GameState,
    IllegalAction,
    Pass,
    Phase,
    Suit,
    SwapTrump,
    Take,
    Transfer,
)


def c(text: str) -> Card:
    return Card.parse(text)


def make_game(
    hands: list[list[str]],
    talon: list[str] | None = None,
    trump: str = "6S",
    attacker: int = 0,
    transfer: bool = False,
    first_bout: bool = False,
    **rules: bool,
) -> Game:
    config = GameConfig(num_players=len(hands), transfer_enabled=transfer, **rules)
    talon_cards = [c(x) for x in (talon or [])]
    state = GameState(
        config=config,
        hands=[[c(x) for x in h] for h in hands],
        talon=talon_cards,
        trump_card=talon_cards[0] if talon_cards else c(trump),
        attacker=attacker,
        defender=(attacker + 1) % len(hands),
        bout_limit=0,
        is_first_bout=first_bout,
    )
    game = Game(state)
    state.bout_limit = game._limit_for(state.defender)
    return game


def test_card_parse_roundtrip():
    for text in ["10H", "AS", "6C", "QD", "2H"]:
        assert str(Card.parse(text)) == text
    with pytest.raises(ValueError):
        Card.parse("1X")


def test_beats():
    assert c("7H").beats(c("6H"), Suit.SPADES)
    assert not c("6H").beats(c("7H"), Suit.SPADES)
    assert c("6S").beats(c("AH"), Suit.SPADES)
    assert not c("AH").beats(c("6S"), Suit.SPADES)
    assert not c("AD").beats(c("6H"), Suit.SPADES)


def test_new_game_deals_and_picks_lowest_trump():
    game = Game.new(GameConfig(num_players=4, deck_size=52), seed=3)
    s = game.state
    assert all(len(h) == 6 for h in s.hands)
    assert len(s.talon) == 52 - 24
    trumps = [(card.rank, p) for p, h in enumerate(s.hands) for card in h if card.suit == s.trump_suit]
    if trumps:
        assert s.attacker == min(trumps)[1]
    assert s.defender == (s.attacker + 1) % 4


def test_only_attacker_opens():
    game = make_game([["7H", "8H"], ["9H", "10H"], ["7C"]], talon=["6S"])
    assert game.current_actors() == {0}
    with pytest.raises(IllegalAction):
        game.apply(2, Attack(c("7C")))


def test_successful_defence_discards_and_defender_attacks_next():
    game = make_game([["7H", "8C"], ["9H", "10C"]], talon=["6S", "6D", "7D"])
    game.apply(0, Attack(c("7H")))
    game.apply(1, Defend(0, c("9H")))
    # Attacker has no matching rank (7 or 9), so the bout ends automatically.
    s = game.state
    assert s.table == []
    assert len(s.discard) == 2
    assert s.attacker == 1 and s.defender == 0


def test_throw_in_requires_pass_to_end_bout():
    game = make_game([["7H", "7C"], ["9H", "10C", "JC"]], talon=["6S", "6D"])
    game.apply(0, Attack(c("7H")))
    game.apply(1, Defend(0, c("9H")))
    assert Pass() in game.legal_actions(0)
    assert Attack(c("7C")) in game.legal_actions(0)
    game.apply(0, Attack(c("7C")))
    game.apply(1, Defend(1, c("10C")))
    # Attacker is now out of cards -> bout ends.
    assert game.state.table == []


def test_throw_in_limit_is_defender_hand_size():
    game = make_game([["7H", "7C", "7D"], ["AS"]], talon=["6S", "8D"])
    game.apply(0, Attack(c("7H")))
    assert game.legal_actions(0) == []  # limit of 1 reached
    assert game.state.bout_limit == 1


def test_first_bout_limit():
    hands = [["7H", "7C", "7D", "7S", "8H", "8C"], ["AS", "KS", "QS", "JS", "10S", "9S"]]
    game = make_game(hands, talon=["6S"], first_bout=True)
    assert game.state.bout_limit == 5


def test_take_allows_throw_ins_then_defender_picks_up():
    game = make_game(
        [["7H", "7C"], ["6H", "8D", "9D"], ["7D", "QC"]],
        talon=["6S", "AD", "AC", "KD"],
    )
    game.apply(0, Attack(c("7H")))
    game.apply(1, Take())
    assert game.state.phase is Phase.DEFENDER_TAKING
    assert game.legal_actions(1) == []
    game.apply(2, Attack(c("7D")))
    game.apply(0, Attack(c("7C")))
    # Limit (3) reached -> defender picks up automatically.
    s = game.state
    assert s.table == []
    assert {"7H", "7D", "7C"} <= {str(x) for x in s.hands[1]}
    # Defender is skipped; seat 2 attacks seat 0.
    assert s.attacker == 2 and s.defender == 0


def test_take_ends_when_all_pass():
    game = make_game([["7H", "7C"], ["6H", "8D", "9D"]], talon=["6S", "AD"])
    game.apply(0, Attack(c("7H")))
    game.apply(1, Take())
    assert Pass() in game.legal_actions(0)
    game.apply(0, Pass())
    assert game.state.table == []
    assert game.state.attacker == 0


def test_only_main_attacker_throws_in_when_pile_on_disabled():
    hands = [["7H", "8C"], ["9H", "10C", "JC"], ["7D", "QC"]]
    talon = ["6S", "AD", "AC"]
    game = make_game(hands, talon=talon)
    game.apply(0, Attack(c("7H")))
    assert Attack(c("7D")) in game.legal_actions(2)

    game = make_game(hands, talon=talon, all_players_throw_in=False)
    game.apply(0, Attack(c("7H")))
    assert game.legal_actions(2) == []
    game.apply(1, Defend(0, c("9H")))
    # Neither the main attacker (no 7 or 9 left) nor seat 2 may add, so it's bito.
    assert game.state.table == []


def test_take_is_immediate_when_throw_in_after_take_disabled():
    game = make_game(
        [["7H", "7C"], ["6H", "8D", "9D"]],
        talon=["6S", "AD"],
        throw_in_after_take=False,
    )
    game.apply(0, Attack(c("7H")))
    game.apply(1, Take())
    s = game.state
    assert s.table == []
    assert c("7H") in s.hands[1] and c("7C") in s.hands[0]


def test_transfer_moves_attack_to_next_player():
    game = make_game(
        [["7H", "8C"], ["7C", "9D"], ["AH", "KH", "QD"]],
        talon=["6S", "6D"],
        transfer=True,
    )
    game.apply(0, Attack(c("7H")))
    assert Transfer(c("7C")) in game.legal_actions(1)
    game.apply(1, Transfer(c("7C")))
    s = game.state
    assert s.attacker == 1 and s.defender == 2
    assert len(s.table) == 2


def test_transfer_rejected_when_disabled_or_after_defence():
    game = make_game([["7H", "8C"], ["7C", "9D"], ["AH", "KH"]], talon=["6S"])
    game.apply(0, Attack(c("7H")))
    assert not any(isinstance(a, Transfer) for a in game.legal_actions(1))

    game = make_game([["7H", "7D"], ["7C", "8H", "9D"], ["AH", "KH", "QH"]], talon=["6S"], transfer=True)
    game.apply(0, Attack(c("7H")))
    game.apply(1, Defend(0, c("8H")))
    game.apply(0, Attack(c("7D")))
    assert not any(isinstance(a, Transfer) for a in game.legal_actions(1))


def test_transfer_rejected_when_target_has_too_few_cards():
    game = make_game([["7H", "8C"], ["7C", "9D"], ["AH"]], talon=["6S"], transfer=True)
    game.apply(0, Attack(c("7H")))
    assert not any(isinstance(a, Transfer) for a in game.legal_actions(1))


def test_draw_order_attacker_first_defender_last():
    game = make_game(
        [["7H"], ["9H", "10C"], ["QC"]],
        talon=["6S", "AD", "KD"],  # draws pop from the end: KD, AD, then trump 6S
    )
    game.apply(0, Attack(c("7H")))
    game.apply(1, Defend(0, c("9H")))
    s = game.state
    assert [str(x) for x in s.hands[0]] == ["KD", "AD", "6S"]
    assert len(s.hands[1]) == 1  # defender gets nothing, talon exhausted
    assert s.talon == []


def test_game_ends_with_durak():
    game = make_game([["7H"], ["9C", "10C"]], trump="6S", first_out_wins=False)
    game.apply(0, Attack(c("7H")))
    game.apply(1, Take())
    s = game.state
    assert s.phase is Phase.FINISHED
    assert s.durak == 1
    assert s.out_order == [0]


def test_game_ends_in_draw():
    game = make_game([["7H"], ["9H"]], trump="6S", first_out_wins=False)
    game.apply(0, Attack(c("7H")))
    game.apply(1, Defend(0, c("9H")))
    s = game.state
    assert s.phase is Phase.FINISHED
    assert s.durak is None
    assert sorted(s.out_order) == [0, 1]


def test_first_out_wins_ends_game_as_soon_as_a_hand_empties():
    game = make_game([["7H"], ["9H", "10C"], ["AD", "KD"]], trump="6S", first_out_wins=True)
    game.apply(0, Attack(c("7H")))
    s = game.state
    assert s.phase is Phase.FINISHED
    assert s.winner == 0 and s.out_order == [0]
    assert s.durak is None
    assert game.view(2).winner == 0


def test_first_out_wins_defender_can_win_mid_bout():
    game = make_game([["7H", "8C"], ["9H"], ["AD", "KD"]], trump="6S", first_out_wins=True)
    game.apply(0, Attack(c("7H")))
    game.apply(1, Defend(0, c("9H")))
    assert game.state.winner == 1


def test_first_out_wins_goes_to_first_hand_emptied_when_deck_runs_out():
    # The last card in the deck refills the attacker; seat 2 emptied their hand
    # before the defender did, so seat 2 wins rather than it being a draw.
    game = make_game([["7H"], ["9H", "8C"], ["7C"]], talon=["6S"], first_out_wins=True)
    game.apply(0, Attack(c("7H")))
    game.apply(2, Attack(c("7C")))
    game.apply(1, Defend(0, c("9H")))
    game.apply(1, Defend(1, c("8C")))
    s = game.state
    assert s.phase is Phase.FINISHED
    assert s.winner == 2
    assert s.hands[0] == [c("6S")]


def test_first_out_wins_waits_for_empty_deck():
    game = make_game([["7H"], ["9H", "10C"], ["AD", "KD"]], talon=["6S", "8C"], first_out_wins=True)
    game.apply(0, Attack(c("7H")))
    game.apply(1, Defend(0, c("9H")))
    assert not game.finished
    assert sorted(game.state.hands[0]) == sorted([c("8C"), c("6S")])


def test_lowest_trump_swaps_for_face_up_trump():
    # 36-card deck, so the lowest trump is the 6.
    game = make_game([["6S", "7H"], ["8H", "9H"]], talon=["QS", "AD", "KD"])
    assert SwapTrump() in game.legal_actions(0)
    assert SwapTrump() not in game.legal_actions(1)

    events = game.apply(0, SwapTrump())
    s = game.state
    assert {str(x) for x in s.hands[0]} == {"QS", "7H"}
    assert s.trump_card == c("6S") and s.talon[0] == c("6S")
    assert game.view(1).trump_card == c("6S")
    assert events[0].kind == "trump_swap"
    assert SwapTrump() not in game.legal_actions(0)


def test_swap_uses_two_with_52_card_deck():
    config = GameConfig(num_players=2, deck_size=52)
    game = make_game([["2S", "6S"], ["8H"]], talon=["QS", "AD"])
    game.state.config = config
    assert SwapTrump() in game.legal_actions(0)
    game.apply(0, SwapTrump())
    assert game.state.trump_card == c("2S")


def test_swap_unavailable_after_trump_drawn_or_disabled():
    game = make_game([["6S", "7H"], ["8H", "9H"]], trump="QS")  # talon empty
    assert SwapTrump() not in game.legal_actions(0)

    game = make_game([["6S", "7H"], ["8H", "9H"]], talon=["QS", "AD"])
    game.state.config = GameConfig(num_players=2, trump_swap_enabled=False)
    assert SwapTrump() not in game.legal_actions(0)


def test_view_hides_other_hands():
    game = Game.new(GameConfig(num_players=3), seed=0)
    view = game.view(1).to_dict()
    assert len(view["hand"]) == 6
    assert view["hand_counts"] == [6, 6, 6]
    assert "hands" not in view


def test_clone_is_independent():
    game = Game.new(GameConfig(), seed=0)
    clone = game.clone()
    action = game.legal_actions(game.state.attacker)[0]
    game.apply(game.state.attacker, action)
    assert clone.state.table == []
