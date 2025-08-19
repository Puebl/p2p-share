import asyncio
import json
import os
import time
import uuid
import aiohttp
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.signaling import BYE

async def get_peers(tracker_url: str, room: str):
    async with aiohttp.ClientSession() as s:
        async with s.get(f"{tracker_url}/join", params={"room": room}) as r:
            j = await r.json()
            return j["peer_id"], set(j["peers"]) - {j["peer_id"]}

async def receive(tracker: str, room: str, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    _self_id, _others = await get_peers(tracker, room)
    pc = RTCPeerConnection()

    start_time = None
    total_bytes = 0
    current_file = None
    f = None

    @pc.on("datachannel")
    def on_datachannel(channel):
        @channel.on("message")
        def on_message(message):
            nonlocal start_time, total_bytes, current_file, f
            if isinstance(message, str) and message.startswith("META:"):
                meta = json.loads(message[5:])
                current_file = os.path.join(out_dir, meta["name"])
                os.makedirs(os.path.dirname(current_file), exist_ok=True)
                f = open(current_file, "wb")
                start_time = time.time()
                total_bytes = 0
            elif message == BYE:
                if f:
                    f.close()
                    f = None
                if start_time is not None:
                    dt = max(time.time() - start_time, 1e-6)
                    print(f"Done. {total_bytes/1e6:.2f} MB in {dt:.2f}s => {total_bytes/1e6/dt:.2f} MB/s")
            else:
                if isinstance(message, (bytes, bytearray)) and f is not None:
                    f.write(message)
                    total_bytes += len(message)

    # Manual signaling: paste offer from sender, produce answer
    offer_sdp = input("Paste SENDER OFFER SDP, then press Enter:\n")
    await pc.setRemoteDescription(RTCSessionDescription(sdp=offer_sdp, type="offer"))
    await pc.setLocalDescription(await pc.createAnswer())
    print("Receiver ANSWER SDP (copy to sender):\n")
    print(pc.localDescription.sdp)
    print("--- END ANSWER ---")

    await asyncio.Event().wait()

async def send(tracker: str, room: str, file_path: str):
    _self_id, _others = await get_peers(tracker, room)
    pc = RTCPeerConnection()

    channel = pc.createDataChannel("file")

    @channel.on("open")
    def on_open():
        asyncio.ensure_future(_send_file(channel, file_path))

    await pc.setLocalDescription(await pc.createOffer())
    offer_sdp = pc.localDescription.sdp
    print("Sender OFFER SDP (copy to receiver):\n")
    print(offer_sdp)
    print("--- END OFFER ---")
    answer_sdp = input("Paste RECEIVER ANSWER SDP, then press Enter:\n")
    await pc.setRemoteDescription(RTCSessionDescription(sdp=answer_sdp, type="answer"))

    await asyncio.Event().wait()

async def _send_file(channel, path: str):
    name = os.path.basename(path)
    size = os.path.getsize(path)
    meta = {"name": name, "size": size}
    channel.send("META:" + json.dumps(meta))
    start = time.time()
    total = 0
    with open(path, "rb") as f:
        while True:
            chunk = f.read(32 * 1024)
            if not chunk:
                break
            channel.send(chunk)
            total += len(chunk)
    channel.send(BYE)
    dt = max(time.time() - start, 1e-6)
    print(f"Sent {total/1e6:.2f} MB in {dt:.2f}s => {total/1e6/dt:.2f} MB/s")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="P2P peer")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_recv = sub.add_parser("receive")
    p_recv.add_argument("--tracker", required=True)
    p_recv.add_argument("--room", required=True)
    p_recv.add_argument("--out", required=True)

    p_send = sub.add_parser("send")
    p_send.add_argument("--tracker", required=True)
    p_send.add_argument("--room", required=True)
    p_send.add_argument("--file", required=True)

    args = parser.parse_args()

    if args.cmd == "receive":
        asyncio.run(receive(args.tracker, args.room, args.out))
    else:
        asyncio.run(send(args.tracker, args.room, args.file))
