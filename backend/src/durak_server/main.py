from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from .protocol import CreateRoomRequest, JoinRoomRequest, SeatTicket
from .rooms import RoomError, RoomManager
from .ws import create_ws_router

FRONTEND_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"


def create_app() -> FastAPI:
    app = FastAPI(title="Durak")
    manager = RoomManager()
    app.state.rooms = manager

    # Handlers are `async def` on purpose: they then run on the event loop like
    # the WebSocket handlers, so room state is never mutated from two threads.

    @app.post("/api/rooms")
    async def create_room(req: CreateRoomRequest) -> SeatTicket:
        try:
            room = manager.create(req.settings)
        except RoomError as exc:
            raise HTTPException(503, str(exc)) from None
        seat, token = room.add_seat(req.name)
        return SeatTicket(code=room.code, token=token, seat=seat)

    @app.post("/api/rooms/{code}/join")
    async def join_room(code: str, req: JoinRoomRequest) -> SeatTicket:
        try:
            room = manager.get(code)
            seat, token = room.add_seat(req.name)
        except KeyError:
            raise HTTPException(404, "room not found") from None
        except RoomError as exc:
            raise HTTPException(409, str(exc)) from None
        return SeatTicket(code=room.code, token=token, seat=seat)

    @app.get("/api/rooms/{code}")
    async def get_room(code: str) -> dict:
        # Deliberately minimal: player names are only visible to seated players.
        try:
            room = manager.get(code)
        except KeyError:
            raise HTTPException(404, "room not found") from None
        return {
            "code": room.code,
            "settings": room.settings.model_dump(),
            "player_count": len(room.seats),
            "started": room.game is not None,
        }

    app.include_router(create_ws_router(manager))

    # In production, serve the built frontend from the same origin.
    if FRONTEND_DIST.is_dir():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

    return app


app = create_app()
