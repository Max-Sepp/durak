"""Fixed-size observation and action encodings for the neural network.

Everything is relative to the seat being encoded: seat 0 is "me", seat 1 the next
player clockwise, and so on, padded to 6 seats. One network then serves every
table size from 2 to 6. The deck (52 cards) and rules are fixed by `ai_config`,
so neither is an input.
"""

from __future__ import annotations

import numpy as np

from durak_engine import (
    Action,
    Attack,
    Card,
    Defend,
    Pass,
    Phase,
    PlayerView,
    Rank,
    Suit,
    SwapTrump,
    Take,
    Transfer,
)

from ..tracker import CardTracker

ENCODING_VERSION = 1

MAX_PLAYERS = 6
MAX_TABLE = 6  # max_bout_cards: the most attacks a bout can hold
NUM_CARDS = 52
SUITS = list(Suit)

# ------------------------------------------------------------------ cards


def card_index(card: Card) -> int:
    return (card.rank - Rank.TWO) * len(SUITS) + SUITS.index(card.suit)


ALL_CARDS = sorted(
    (Card(rank, suit) for rank in Rank for suit in Suit), key=card_index
)


def index_card(index: int) -> Card:
    return ALL_CARDS[index]


# ------------------------------------------------------------ observation

# Per-card channels, each a 52-wide plane.
CH_HAND = 0
CH_ATTACK = 1  # + table slot, 6 channels
CH_DEFENSE = CH_ATTACK + MAX_TABLE  # + table slot, 6 channels
CH_DISCARD = CH_DEFENSE + MAX_TABLE
CH_KNOWN = CH_DISCARD + 1  # + relative seat - 1, 5 channels
CH_FACE_UP = CH_KNOWN + MAX_PLAYERS - 1
CH_UNSEEN = CH_FACE_UP + 1
CH_TRUMP = CH_UNSEEN + 1  # every card of the trump suit
NUM_CHANNELS = CH_TRUMP + 1

NUM_SCALARS = (
    MAX_PLAYERS  # hand counts
    + MAX_PLAYERS  # cards not yet seen in each hand
    + 2  # talon, discard counts
    + len(SUITS)  # trump suit
    + 3  # my role: attacker, defender, other
    + MAX_PLAYERS  # attacker seat
    + MAX_PLAYERS  # defender seat
    + 2  # phase: attacking, defender taking
    + 2  # bout limit, attacks on the table
    + MAX_PLAYERS  # passed
    + MAX_PLAYERS  # out
    + 1  # first bout
    + MAX_PLAYERS - 1  # number of players, 2..6
)

OBS_DIM = NUM_CHANNELS * NUM_CARDS + NUM_SCALARS


def encode_observation(view: PlayerView, tracker: CardTracker) -> np.ndarray:
    """A flat float32 vector of length OBS_DIM describing `view` from its own seat.

    `tracker` must belong to the same seat and be up to date with `view`.
    """
    me = view.you
    n = len(view.hand_counts)

    def rel(seat: int) -> int:
        return (seat - me) % n

    cards = np.zeros((NUM_CHANNELS, NUM_CARDS), dtype=np.float32)
    cards[CH_HAND, [card_index(c) for c in view.hand]] = 1
    for slot, (attack, defense) in enumerate(view.table):
        cards[CH_ATTACK + slot, card_index(attack)] = 1
        if defense is not None:
            cards[CH_DEFENSE + slot, card_index(defense)] = 1
    cards[CH_DISCARD, [card_index(c) for c in tracker.discard]] = 1
    for seat, known in enumerate(tracker.known):
        if seat != me and known:
            cards[CH_KNOWN + rel(seat) - 1, [card_index(c) for c in known]] = 1
    if view.trump_card is not None:
        cards[CH_FACE_UP, card_index(view.trump_card)] = 1
    cards[CH_UNSEEN, [card_index(c) for c in tracker.unseen()]] = 1
    trump = SUITS.index(Suit(view.trump_suit))
    cards[CH_TRUMP, trump :: len(SUITS)] = 1

    scalars = np.zeros(NUM_SCALARS, dtype=np.float32)
    i = 0

    def put(values) -> None:
        nonlocal i
        values = np.asarray(values, dtype=np.float32)
        scalars[i : i + len(values)] = values
        i += len(values)

    def seats(values_by_seat) -> np.ndarray:
        out = np.zeros(MAX_PLAYERS, dtype=np.float32)
        for seat, value in enumerate(values_by_seat):
            out[rel(seat)] = value
        return out

    def one_hot(index: int, size: int) -> np.ndarray:
        out = np.zeros(size, dtype=np.float32)
        out[index] = 1
        return out

    # Hands can grow to dozens of cards; a log scale keeps them in [0, 1] while
    # still telling 1, 2 and 3 cards apart, which matters most.
    put(_count_scale(seats(view.hand_counts)))
    put(_count_scale(seats([tracker.unknown_count(p) for p in range(n)])))
    put([view.talon_count / 40, view.discard_count / NUM_CARDS])
    put(one_hot(trump, len(SUITS)))
    role = 0 if view.attacker == me else 1 if view.defender == me else 2
    put(one_hot(role, 3))
    put(one_hot(rel(view.attacker), MAX_PLAYERS))
    put(one_hot(rel(view.defender), MAX_PLAYERS))
    put([view.phase == Phase.ATTACKING.value, view.phase == Phase.DEFENDER_TAKING.value])
    put([view.bout_limit / MAX_TABLE, len(view.table) / MAX_TABLE])
    put(seats([p in view.passed for p in range(n)]))
    put(seats([p in view.out_order for p in range(n)]))
    put([tracker.first_bout])
    put(one_hot(n - 2, MAX_PLAYERS - 1))
    assert i == NUM_SCALARS

    return np.concatenate([cards.ravel(), scalars])


def _count_scale(counts: np.ndarray) -> np.ndarray:
    return np.log1p(counts) / np.log1p(NUM_CARDS)


# ----------------------------------------------------------------- actions

ATTACK_BASE = 0
TRANSFER_BASE = ATTACK_BASE + NUM_CARDS
DEFEND_BASE = TRANSFER_BASE + NUM_CARDS  # + slot * 52 + card
TAKE = DEFEND_BASE + MAX_TABLE * NUM_CARDS
PASS = TAKE + 1
SWAP_TRUMP = PASS + 1
WAIT = SWAP_TRUMP + 1  # act() returning None
NUM_ACTIONS = WAIT + 1


def action_to_index(action: Action | None) -> int:
    match action:
        case None:
            return WAIT
        case Attack(card):
            return ATTACK_BASE + card_index(card)
        case Transfer(card):
            return TRANSFER_BASE + card_index(card)
        case Defend(slot, card):
            if not 0 <= slot < MAX_TABLE:
                raise ValueError(f"table slot out of range: {slot}")
            return DEFEND_BASE + slot * NUM_CARDS + card_index(card)
        case Take():
            return TAKE
        case Pass():
            return PASS
        case SwapTrump():
            return SWAP_TRUMP
    raise TypeError(f"unknown action: {action!r}")


def index_to_action(index: int) -> Action | None:
    if not 0 <= index < NUM_ACTIONS:
        raise ValueError(f"action index out of range: {index}")
    if index < TRANSFER_BASE:
        return Attack(index_card(index - ATTACK_BASE))
    if index < DEFEND_BASE:
        return Transfer(index_card(index - TRANSFER_BASE))
    if index < TAKE:
        slot, card = divmod(index - DEFEND_BASE, NUM_CARDS)
        return Defend(slot, index_card(card))
    return {TAKE: Take(), PASS: Pass(), SWAP_TRUMP: SwapTrump(), WAIT: None}[index]


def legal_mask(legal: list[Action], can_wait: bool) -> np.ndarray:
    """Boolean mask over NUM_ACTIONS: the legal actions, plus WAIT if allowed."""
    mask = np.zeros(NUM_ACTIONS, dtype=bool)
    mask[[action_to_index(a) for a in legal]] = True
    mask[WAIT] = can_wait
    return mask
