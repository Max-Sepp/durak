from __future__ import annotations

import asyncio
import secrets
import string
import time
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket

from durak_engine import Event, Game, GameConfig, action_to_dict

from .protocol import RoomSettings

CODE_ALPHABET = string.ascii_uppercase.replace("O", "").replace("I", "") + "23456789"
CODE_LENGTH = 6  # 32**6 ≈ 1e9 codes, so guessing a live room is impractical
IDLE_ROOM_SECONDS = 6 * 60 * 60
MAX_PLAYERS = 6
MAX_ROOMS = 1000


class RoomError(Exception):
    pass


@dataclass
class Seat:
    """A place at the table. Today every seat is a human with a token; an AI
    controller can occupy a seat later without changing the engine."""

    name: str
    token: str
    connected: bool = False


@dataclass
class Room:
    code: str
    settings: RoomSettings
    seats: list[Seat] = field(default_factory=list)
    game: Game | None = None
    last_events: list[Event] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    connections: dict[WebSocket, int] = field(default_factory=dict)
    last_activity: float = field(default_factory=time.monotonic)

    @property
    def host_seat(self) -> int:
        return 0

    def seat_for_token(self, token: str) -> int | None:
        # compare_digest rejects non-ASCII str, so compare bytes instead.
        given = token.encode()
        for i, seat in enumerate(self.seats):
            if secrets.compare_digest(seat.token.encode(), given):
                return i
        return None

    def add_seat(self, name: str) -> tuple[int, str]:
        if self.game is not None:
            raise RoomError("game already started")
        if len(self.seats) >= MAX_PLAYERS:
            raise RoomError(f"room is full ({MAX_PLAYERS} players max)")
        token = secrets.token_urlsafe(24)
        self.seats.append(Seat(name=name, token=token))
        self.touch()
        return len(self.seats) - 1, token

    def start(self, seat: int) -> None:
        if seat != self.host_seat:
            raise RoomError("only the host can start the game")
        if len(self.seats) < 2:
            raise RoomError("need at least two players")
        self._new_game()

    def rematch(self) -> None:
        if self.game is None or not self.game.finished:
            raise RoomError("game is not over yet")
        self._new_game()

    def _new_game(self) -> None:
        config = GameConfig(
            num_players=len(self.seats),
            deck_size=self.settings.deck_size,
            transfer_enabled=self.settings.transfer_enabled,
            trump_swap_enabled=self.settings.trump_swap_enabled,
            all_players_throw_in=self.settings.all_players_throw_in,
            throw_in_after_take=self.settings.throw_in_after_take,
            first_out_wins=self.settings.first_out_wins,
        )
        self.game = Game.new(config)
        self.last_events = []

    def touch(self) -> None:
        self.last_activity = time.monotonic()

    def snapshot(self, seat: int) -> dict[str, Any]:
        """Everything one seat should see, sent after every change."""
        room = {
            "code": self.code,
            "settings": self.settings.model_dump(),
            "seats": [{"name": s.name, "connected": s.connected} for s in self.seats],
            "host_seat": self.host_seat,
            "max_players": MAX_PLAYERS,
            "you": seat,
            "started": self.game is not None,
        }
        game = None
        if self.game is not None:
            game = {
                "view": self.game.view(seat).to_dict(),
                "legal_actions": [action_to_dict(a) for a in self.game.legal_actions(seat)],
                "events": [e.to_dict() for e in self.last_events],
            }
        return {"type": "room", "room": room, "game": game}


class RoomManager:
    def __init__(self) -> None:
        self.rooms: dict[str, Room] = {}

    def create(self, settings: RoomSettings) -> Room:
        self._prune()
        if len(self.rooms) >= MAX_ROOMS:
            raise RoomError("server is busy, try again later")
        while True:
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
            if code not in self.rooms:
                break
        room = Room(code=code, settings=settings)
        self.rooms[code] = room
        return room

    def get(self, code: str) -> Room:
        room = self.rooms.get(code.upper())
        if room is None:
            raise KeyError(code)
        return room

    def _prune(self) -> None:
        cutoff = time.monotonic() - IDLE_ROOM_SECONDS
        for code, room in list(self.rooms.items()):
            if not room.connections and room.last_activity < cutoff:
                del self.rooms[code]
