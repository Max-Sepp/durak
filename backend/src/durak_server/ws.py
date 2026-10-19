from __future__ import annotations

import asyncio
import json
import time
from collections import deque

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from durak_engine import IllegalAction, action_from_dict

from .protocol import ActionMessage, ClientMessage, RematchMessage, StartMessage
from .rooms import Room, RoomError, RoomManager

AUTH_TIMEOUT_SECONDS = 10
MAX_MESSAGE_CHARS = 4096
RATE_LIMIT_MESSAGES = 20
RATE_LIMIT_WINDOW_SECONDS = 1.0

# Application close codes (4000-4999). The client stops reconnecting on these.
CLOSE_AUTH_REQUIRED = 4401
CLOSE_FORBIDDEN = 4403
CLOSE_NOT_FOUND = 4404
CLOSE_REPLACED = 4409
CLOSE_TOO_BIG = 1009


class RateLimiter:
    """Sliding-window limit on messages per connection."""

    def __init__(self) -> None:
        self.times: deque[float] = deque()

    def allow(self) -> bool:
        now = time.monotonic()
        while self.times and now - self.times[0] > RATE_LIMIT_WINDOW_SECONDS:
            self.times.popleft()
        if len(self.times) >= RATE_LIMIT_MESSAGES:
            return False
        self.times.append(now)
        return True


def create_ws_router(manager: RoomManager) -> APIRouter:
    router = APIRouter()

    @router.websocket("/ws/{code}")
    async def room_socket(websocket: WebSocket, code: str) -> None:
        # Accept first so rejections reach the browser as close codes; closing
        # before the handshake surfaces as a generic 1006 the client retries.
        await websocket.accept()
        authed = await _authenticate(websocket, manager, code)
        if authed is None:
            return
        room, seat = authed

        async with room.lock:
            # One live connection per seat: the newest one wins.
            for other, other_seat in list(room.connections.items()):
                if other_seat == seat:
                    room.connections.pop(other)
                    await _close(other, CLOSE_REPLACED, "seat opened elsewhere")
            room.connections[websocket] = seat
            room.seats[seat].connected = True
            room.touch()
            await broadcast(room)

        limiter = RateLimiter()
        try:
            while True:
                text = await websocket.receive_text()
                if len(text) > MAX_MESSAGE_CHARS:
                    await _close(websocket, CLOSE_TOO_BIG, "message too large")
                    return
                if not limiter.allow():
                    await websocket.send_json({"type": "error", "message": "slow down"})
                    continue
                async with room.lock:
                    try:
                        handle_message(room, seat, json.loads(text))
                    except (RoomError, IllegalAction, ValidationError, ValueError) as exc:
                        await websocket.send_json({"type": "error", "message": _message(exc)})
                        continue
                    room.touch()
                    await broadcast(room)
        except (WebSocketDisconnect, RuntimeError, KeyError):
            # Disconnects, plus binary frames / receiving after a server-side close.
            pass
        finally:
            async with room.lock:
                room.connections.pop(websocket, None)
                room.seats[seat].connected = seat in room.connections.values()
                await broadcast(room)

    return router


async def _authenticate(
    websocket: WebSocket, manager: RoomManager, code: str
) -> tuple[Room, int] | None:
    """The first message must be {"type": "auth", "token": ...}. The token is
    kept out of the URL so it never lands in access logs or proxy logs."""
    try:
        text = await asyncio.wait_for(websocket.receive_text(), AUTH_TIMEOUT_SECONDS)
        msg = json.loads(text) if len(text) <= MAX_MESSAGE_CHARS else None
    except (TimeoutError, WebSocketDisconnect, RuntimeError, KeyError, ValueError):
        msg = None
    token = msg.get("token") if isinstance(msg, dict) and msg.get("type") == "auth" else None
    if not isinstance(token, str):
        await _close(websocket, CLOSE_AUTH_REQUIRED, "authentication required")
        return None
    try:
        room = manager.get(code)
    except KeyError:
        await _close(websocket, CLOSE_NOT_FOUND, "room not found")
        return None
    seat = room.seat_for_token(token)
    if seat is None:
        await _close(websocket, CLOSE_FORBIDDEN, "invalid token")
        return None
    return room, seat


async def _close(websocket: WebSocket, code: int, reason: str) -> None:
    try:
        await websocket.close(code=code, reason=reason)
    except RuntimeError:
        pass  # already closed


def handle_message(room: Room, seat: int, raw: object) -> None:
    msg = ClientMessage.model_validate({"msg": raw}).msg
    match msg:
        case StartMessage():
            if room.game is not None:
                raise RoomError("game already started")
            room.start(seat)
        case RematchMessage():
            room.rematch()
        case ActionMessage(action=payload):
            if room.game is None:
                raise RoomError("game has not started")
            action = action_from_dict(payload.model_dump(exclude_none=True))
            room.last_events = room.game.apply(seat, action)


async def broadcast(room: Room) -> None:
    for ws, seat in list(room.connections.items()):
        try:
            await ws.send_json(room.snapshot(seat))
        except Exception:
            room.connections.pop(ws, None)


def _message(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        return "malformed message"
    if isinstance(exc, (RoomError, IllegalAction)):
        return str(exc)
    return "malformed message"
