# P2P Share CLI

Minimal P2P file sharing over WebRTC data channels.

- Peer discovery: simple tracker (HTTP) using `aiohttp`
- Transport: `aiortc` data channels
- CLI: send/recv files between peers

## Quickstart

1) Create and start tracker (discovery server):

```
python tracker.py --host 0.0.0.0 --port 8080
```

2) Start peer A (receiver):
```
python peer.py receive --tracker http://127.0.0.1:8080 --room test --out downloads/
```

3) Start peer B (sender):
```
python peer.py send --tracker http://127.0.0.1:8080 --room test --file path/to/file.bin
```

## Metrics
- Throughput (MB/s) during transfer
- NAT traversal success rate (log if direct/relay; stretch: TURN integration)

## Notes
- For local demo, run both peers on same machine or LAN.
- TURN is not included in MVP; STUN default servers from `aiortc` are used.
