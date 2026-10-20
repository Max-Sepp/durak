from __future__ import annotations

from abc import ABC, abstractmethod

from durak_engine import Action, Event, GameConfig, Pass, PlayerView

from .config import check_ai_config
from .tracker import CardTracker


class Agent(ABC):
    """A Durak player that only sees what its seat may see.

    Agents get `PlayerView`s and `Event`s, never the `Game` itself, which is the
    same information a websocket client receives. The arena (or later a server
    seat) calls `reset` once per game, `observe` after every move by anyone, and
    `act` whenever this seat has legal actions.
    """

    name: str = "agent"

    seat: int
    config: GameConfig
    tracker: CardTracker

    def reset(self, seat: int, config: GameConfig, view: PlayerView) -> None:
        check_ai_config(config)
        self.seat = seat
        self.config = config
        self.tracker = CardTracker(seat, config, view)

    def observe(self, view: PlayerView, events: list[Event]) -> None:
        self.tracker.update(view, events)

    @abstractmethod
    def act(self, view: PlayerView, legal: list[Action]) -> Action | None:
        """Pick one of `legal`, or return None to wait.

        Several seats may act at once (throw-ins, trump swaps), and an attacker
        may want to hold back until the defender has answered. None means "not
        now": it becomes `Pass` when passing is legal. A defender facing an
        unbeaten card and an attacker opening a bout must not wait.
        """


def may_wait(view: PlayerView, legal: list[Action]) -> bool:
    """Whether `act` may return None: only a non-defender, only while the defender
    still has an unbeaten card to answer (so someone else is sure to move), and
    only when passing isn't on offer (where None would just mean Pass)."""
    return (
        view.you != view.defender
        and Pass() not in legal
        and any(d is None for _, d in view.table)
    )
