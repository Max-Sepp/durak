# Durak

Online Durak (Podkidnoy, with optional Perevodnoy/transfer) for 2–6 players.

- `backend/src/durak_engine` — pure-Python rules engine, no third-party dependencies.
- `backend/src/durak_server` — FastAPI server: REST for rooms, WebSockets for play.
- `frontend` — Vite + React + TypeScript + shadcn/ui.

## Development

```sh
# backend (http://localhost:8000)
cd backend
uv run uvicorn durak_server.main:app --reload

# frontend (http://localhost:5173, proxies /api and /ws to the backend)
cd frontend
pnpm install
pnpm dev
```

Open the frontend, create a room, and share the code or invite link. Open a second
browser window (or a private window) to join as another player.

Tests: `cd backend && uv run pytest`. Frontend type check + build: `cd frontend && pnpm build`.

For a single-process deployment, run `pnpm build`; the server then serves
`frontend/dist` itself.

### Deploying publicly

- Don't expose `pnpm dev` to the internet. The Vite dev server is for local and LAN testing only. Build the frontend and serve it from uvicorn instead.
- Put the app behind HTTPS (a reverse proxy such as Caddy or nginx), so seat tokens and websockets travel over TLS (`wss://`).
- Cap websocket frame size in uvicorn as well as in the app:
  `uv run uvicorn durak_server.main:app --host 0.0.0.0 --ws-max-size 16384`
- Rooms live in memory in a single process. Run one worker and don't use `--workers N`.

### Security model

- Seat tokens come from `secrets.token_urlsafe(24)`, are compared in constant time, and are sent as the first websocket message (`{"type": "auth", "token": ...}`), never in a URL.
- Room codes are 6 characters drawn with `secrets.choice` (about 10⁹ possibilities).
- Deals use `random.SystemRandom` (OS CSPRNG). Pass a `seed` to `Game.new` only for tests or AI training.
- Each player only ever receives their own hand. Other hands are reduced to counts on the server.
- Limits:
  - 6 players per room and 1000 live rooms.
  - One live connection per seat; a newer connection replaces the older one.
  - 4 KB per message and 20 messages per second per connection.

## Engine API (for writing AIs)

```python
from durak_engine import Game, GameConfig

game = Game.new(GameConfig(num_players=3, deck_size=36, transfer_enabled=True), seed=42)
while not game.finished:
    for player in game.current_actors():
        view = game.view(player)                # what that seat may see
        actions = game.legal_actions(player)    # Attack / Defend / Transfer / Take / Pass / SwapTrump
        game.apply(player, actions[0])
        break
```

- `game.clone()` gives an independent copy for lookahead/search.
- Several players can have legal moves at once (throw-ins), so callers serialise `apply`.
- Players with nothing to throw in are treated as having passed, so play never waits on them.

## Rules implemented

- The holder of the lowest trump attacks first. The first bout allows at most 5 cards; later bouts allow 6, and never more than the defender's hand at the start of the bout.
- Players may throw in cards whose rank is already on the table.

Optional rules are set per room and in `GameConfig`. All of them are on by default:

| Rule | `GameConfig` field | When off |
| --- | --- | --- |
| Transfer (Perevodnoy) | `transfer_enabled` | Defender must beat or take |
| Trump swap | `trump_swap_enabled` | No swapping |
| Everyone piles on | `all_players_throw_in` | Only the main attacker may throw in |
| Pile on after take | `throw_in_after_take` | Defender picks up immediately |
| First out wins | `first_out_wins` | Play continues until one player (the durak) is left |

- Transfer: before any defence, the defender may add a card of the same rank to pass the attack to the next player, provided that player holds enough cards.
- Whoever holds the lowest trump (the 2 with 52 cards, the 6 with 36) may swap it for the face-up trump card under the deck at any time, until that card is drawn.
- After a take, attackers may still throw in up to the limit if "pile on after take" is on. The defender then picks everything up and loses their turn to attack.
- Hands are refilled to 6: main attacker first, defender last. The face-up trump card is drawn last.
- Once the deck is empty, players with no cards are out. With "first out wins" off, the last player holding cards is the durak; if nobody is, it's a draw.
- First out wins: once the deck is empty, the game ends the moment a player plays their last card, and that player is the `winner` (there is no durak). If several players emptied their hands during a bout while the deck still had cards and drawing doesn't refill them, whoever emptied their hand first wins, so there are no draws.
