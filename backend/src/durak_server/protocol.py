from __future__ import annotations

import unicodedata
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, StringConstraints


class RoomSettings(BaseModel):
    deck_size: Literal[36, 52] = 52
    transfer_enabled: bool = True
    trump_swap_enabled: bool = True
    all_players_throw_in: bool = True
    throw_in_after_take: bool = True


def _clean_name(name: str) -> str:
    # Control and invisible formatting characters (e.g. bidi overrides, zero-width
    # spaces) let a name impersonate or visually garble other players' names.
    if any(unicodedata.category(ch) in ("Cc", "Cf") for ch in name):
        raise ValueError("name contains invalid characters")
    return name


PlayerName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=24),
    AfterValidator(_clean_name),
]


class CreateRoomRequest(BaseModel):
    name: PlayerName
    settings: RoomSettings = RoomSettings()


class JoinRoomRequest(BaseModel):
    name: PlayerName


class SeatTicket(BaseModel):
    code: str
    token: str
    seat: int


class ActionPayload(BaseModel):
    kind: Literal["attack", "defend", "transfer", "take", "pass", "swap_trump"]
    card: str | None = Field(default=None, max_length=3)
    attack_index: int | None = Field(default=None, ge=0, le=12)


class StartMessage(BaseModel):
    type: Literal["start"]


class ActionMessage(BaseModel):
    type: Literal["action"]
    action: ActionPayload


class RematchMessage(BaseModel):
    type: Literal["rematch"]


class ClientMessage(BaseModel):
    msg: Annotated[StartMessage | ActionMessage | RematchMessage, Field(discriminator="type")]
