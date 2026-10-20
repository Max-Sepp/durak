import random

import pytest

np = pytest.importorskip("numpy")

from durak_ai import CardTracker, ai_config, may_wait  # noqa: E402
from durak_ai.nn.encoding import (  # noqa: E402
    ALL_CARDS,
    CH_ATTACK,
    CH_DEFENSE,
    CH_DISCARD,
    CH_HAND,
    CH_KNOWN,
    CH_UNSEEN,
    NUM_ACTIONS,
    NUM_CARDS,
    NUM_CHANNELS,
    OBS_DIM,
    WAIT,
    action_to_index,
    card_index,
    encode_observation,
    index_to_action,
    legal_mask,
)
from durak_engine import Game  # noqa: E402


def test_card_indices_cover_the_deck():
    assert len(ALL_CARDS) == NUM_CARDS
    assert [card_index(c) for c in ALL_CARDS] == list(range(NUM_CARDS))


def test_every_action_index_round_trips():
    for i in range(NUM_ACTIONS):
        action = index_to_action(i)
        assert action_to_index(action) == i
    assert index_to_action(WAIT) is None


def plane(obs, channel):
    cards = obs[: NUM_CHANNELS * NUM_CARDS].reshape(NUM_CHANNELS, NUM_CARDS)
    return {ALL_CARDS[i] for i in np.flatnonzero(cards[channel])}


@pytest.mark.parametrize("num_players", [2, 3, 4, 5, 6])
def test_observations_and_masks_follow_the_game(num_players):
    for seed in range(5):
        game = Game.new(ai_config(num_players), seed=seed)
        trackers = [CardTracker(p, game.state.config, game.view(p)) for p in range(num_players)]
        rng = random.Random(seed)
        while not game.finished:
            s = game.state
            for seat, tracker in enumerate(trackers):
                view = game.view(seat)
                obs = encode_observation(view, tracker)
                assert obs.shape == (OBS_DIM,) and obs.dtype == np.float32
                assert np.isfinite(obs).all() and obs.min() >= 0 and obs.max() <= 1

                assert plane(obs, CH_HAND) == set(s.hands[seat])
                for slot, pair in enumerate(s.table):
                    assert plane(obs, CH_ATTACK + slot) == {pair.attack}
                    assert plane(obs, CH_DEFENSE + slot) == ({pair.defense} if pair.defense else set())
                assert plane(obs, CH_DISCARD) == set(s.discard)
                assert plane(obs, CH_UNSEEN) == tracker.unseen()
                # Known cards land in the channel of their holder's relative seat.
                for other, known in enumerate(tracker.known):
                    if other != seat:
                        rel = (other - seat) % num_players
                        assert plane(obs, CH_KNOWN + rel - 1) == known

                legal = game.legal_actions(seat)
                mask = legal_mask(legal, may_wait(view, legal))
                expected = {action_to_index(a) for a in legal}
                if may_wait(view, legal):
                    expected.add(WAIT)
                assert set(np.flatnonzero(mask)) == expected

            player = rng.choice(sorted(game.current_actors()))
            events = game.apply(player, rng.choice(game.legal_actions(player)))
            for seat, tracker in enumerate(trackers):
                tracker.update(game.view(seat), events)
