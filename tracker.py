import asyncio
import uuid
from typing import Dict, Set
from aiohttp import web

# Very small in-memory tracker: rooms -> set(peer_ids)
ROOMS: Dict[str, Set[str]] = {}

async def join(request: web.Request) -> web.Response:
    room = request.query.get("room", "default")
    peer_id = str(uuid.uuid4())
    peers = ROOMS.setdefault(room, set())
    peers.add(peer_id)
    return web.json_response({"peer_id": peer_id, "peers": list(peers)})

async def list_peers(request: web.Request) -> web.Response:
    room = request.query.get("room", "default")
    peers = list(ROOMS.get(room, set()))
    return web.json_response({"peers": peers})

async def leave(request: web.Request) -> web.Response:
    room = request.query.get("room", "default")
    peer_id = request.query.get("peer_id")
    if peer_id and room in ROOMS and peer_id in ROOMS[room]:
        ROOMS[room].remove(peer_id)
    return web.json_response({"ok": True})

def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/join", join)
    app.router.add_get("/peers", list_peers)
    app.router.add_get("/leave", leave)
    return app

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Simple P2P tracker")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    web.run_app(create_app(), host=args.host, port=args.port)
