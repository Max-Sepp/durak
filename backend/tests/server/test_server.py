from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from durak_server.main import create_app
from durak_server.ws import RATE_LIMIT_MESSAGES


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def create_room(client: TestClient, **settings) -> dict:
    res = client.post("/api/rooms", json={"name": "Alice", "settings": settings})
    assert res.status_code == 200
    return res.json()


@contextmanager
def connect(client: TestClient, code: str, token: str):
    with client.websocket_connect(f"/ws/{code}") as ws:
        ws.send_json({"type": "auth", "token": token})
        yield ws


def close_code(ws) -> int:
    with pytest.raises(WebSocketDisconnect) as exc:
        while True:
            ws.receive_json()
    return exc.value.code


def test_create_and_join(client):
    host = create_room(client)
    assert len(host["code"]) == 6
    res = client.post(f"/api/rooms/{host['code']}/join", json={"name": "Bob"})
    assert res.status_code == 200
    assert res.json()["seat"] == 1

    assert client.post("/api/rooms/NOPE12/join", json={"name": "X"}).status_code == 404
    info = client.get(f"/api/rooms/{host['code']}").json()
    assert info["player_count"] == 2 and "players" not in info


def test_room_is_capped_at_six_players(client):
    host = create_room(client)
    for i in range(5):
        assert client.post(f"/api/rooms/{host['code']}/join", json={"name": f"P{i}"}).status_code == 200
    res = client.post(f"/api/rooms/{host['code']}/join", json={"name": "Seventh"})
    assert res.status_code == 409
    assert "6 players max" in res.json()["detail"]


@pytest.mark.parametrize("name", ["   ", "", "a" * 25, "evil‮eman", "zero​width", "nul\x00"])
def test_bad_names_rejected(client, name):
    assert client.post("/api/rooms", json={"name": name}).status_code == 422


def test_name_is_trimmed(client):
    host = client.post("/api/rooms", json={"name": "  Ada  "}).json()
    with connect(client, host["code"], host["token"]) as ws:
        assert ws.receive_json()["room"]["seats"][0]["name"] == "Ada"


@pytest.mark.parametrize("token", ["wrong", "é-non-ascii", ""])
def test_bad_token_rejected_with_close_code(client, token):
    host = create_room(client)
    with connect(client, host["code"], token) as ws:
        assert close_code(ws) == 4403


def test_missing_auth_rejected(client):
    host = create_room(client)
    with client.websocket_connect(f"/ws/{host['code']}") as ws:
        ws.send_json({"type": "start"})
        assert close_code(ws) == 4401


def test_unknown_room_rejected(client):
    with connect(client, "NOPE12", "x") as ws:
        assert close_code(ws) == 4404


def test_token_in_url_is_not_accepted(client):
    host = create_room(client)
    with client.websocket_connect(f"/ws/{host['code']}?token={host['token']}") as ws:
        ws.send_json({"type": "start"})
        assert close_code(ws) == 4401


def test_second_connection_replaces_first(client):
    host = create_room(client)
    with connect(client, host["code"], host["token"]) as first:
        first.receive_json()
        with connect(client, host["code"], host["token"]) as second:
            assert close_code(first) == 4409
            assert second.receive_json()["type"] == "room"


def test_oversized_message_closes_connection(client):
    host = create_room(client)
    with connect(client, host["code"], host["token"]) as ws:
        ws.receive_json()
        ws.send_text("x" * 10_000)
        assert close_code(ws) == 1009


def test_malformed_json_is_an_error_not_a_crash(client):
    host = create_room(client)
    with connect(client, host["code"], host["token"]) as ws:
        ws.receive_json()
        ws.send_text("{not json")
        assert ws.receive_json() == {"type": "error", "message": "malformed message"}
        ws.send_json({"type": "action", "action": {"kind": "attack", "card": "ZZZ"}})
        assert ws.receive_json()["type"] == "error"


def test_rate_limit(client):
    host = create_room(client)
    with connect(client, host["code"], host["token"]) as ws:
        ws.receive_json()
        for _ in range(RATE_LIMIT_MESSAGES + 5):
            ws.send_json({"type": "rematch"})
        replies = [ws.receive_json()["message"] for _ in range(RATE_LIMIT_MESSAGES + 5)]
        assert "slow down" in replies


def test_full_flow_over_websockets(client):
    host = create_room(client, transfer_enabled=True)
    code = host["code"]
    guest = client.post(f"/api/rooms/{code}/join", json={"name": "Bob"}).json()

    with connect(client, code, host["token"]) as ws_a:
        lobby = ws_a.receive_json()
        assert lobby["type"] == "room" and lobby["game"] is None
        assert "token" not in str(lobby)

        with connect(client, code, guest["token"]) as ws_b:
            ws_a.receive_json()  # Bob connected
            ws_b.receive_json()

            ws_b.send_json({"type": "start"})
            assert ws_b.receive_json()["type"] == "error"  # only host may start

            ws_a.send_json({"type": "start"})
            state_a = ws_a.receive_json()["game"]
            state_b = ws_b.receive_json()["game"]

            assert state_a["view"]["you"] == 0 and state_b["view"]["you"] == 1
            assert len(state_a["view"]["hand"]) == 6
            assert set(state_a["view"]["hand"]).isdisjoint(state_b["view"]["hand"])

            attacker = state_a["view"]["attacker"]
            ws_att, st_att = (ws_a, state_a) if attacker == 0 else (ws_b, state_b)
            ws_def = ws_b if attacker == 0 else ws_a
            action = next(a for a in st_att["legal_actions"] if a["kind"] == "attack")
            ws_att.send_json({"type": "action", "action": action})

            after_att = ws_att.receive_json()["game"]
            after_def = ws_def.receive_json()["game"]
            assert after_att["view"]["table"][0]["attack"] == action["card"]
            assert after_def["view"]["table"] == after_att["view"]["table"]
            assert any(a["kind"] == "take" for a in after_def["legal_actions"])

            ws_att.send_json({"type": "action", "action": {"kind": "take"}})
            assert ws_att.receive_json()["type"] == "error"
