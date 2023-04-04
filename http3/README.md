# HTTP/3: Building from Scratch

This project implements HTTP/3 on top of our QUIC implementation.

---

## What is HTTP/3?

**HTTP/3 = HTTP semantics over QUIC**

Same request/response model as HTTP/1.1 and HTTP/2, but using QUIC for transport instead of TCP.

```
HTTP/1.1:  Text format  →  TCP
HTTP/2:    Binary frames →  TCP
HTTP/3:    Binary frames →  QUIC  ← We're building this
```

### Why HTTP/3?

| Problem with TCP | HTTP/3 Solution |
|------------------|-----------------|
| Head-of-line blocking | QUIC streams are independent |
| Slow connection setup | QUIC 0-RTT handshake |
| Connection breaks on IP change | QUIC connection migration |

---

## End Goal

A working HTTP/3 client/server that can:

```
Client                              Server
   │                                   │
   │─── GET /hello HTTP/3 ────────────►│
   │    (over QUIC stream)             │
   │                                   │
   │◄─── 200 OK + "Hello World" ──────│
   │                                   │
```

---

## Project Roadmap

### Phase 1: Frames ✅
HTTP/3 uses binary frames on QUIC streams.

- [x] Step 1: Understand frame format
- [x] Step 2: Encode frames (HEADERS, DATA)
- [x] Step 3: Decode frames

### Phase 2: Headers ✅
HTTP headers (method, path, status) need encoding.

- [x] Step 4: Simple header encoding (plain text, non-QPACK)
- [x] Step 5: Header decoding
- [ ] Step 6: (Optional) QPACK compression

### Phase 3: Request/Response ✅
Map HTTP semantics to QUIC streams.

- [x] Step 7: Build request helper
- [x] Step 8: Build response helper
- [x] Step 9: Parse request/response helpers

### Phase 4: Integration ✅
Connect to our QUIC implementation.

- [x] Step 10: Create HTTP/3 client (quic/quic_client.py)
- [x] Step 11: Create HTTP/3 server (http3/server.py)
- [x] Step 12: End-to-end test: `GET /hello` → `(200, b'Hello World')`

---

## HTTP/3 Frame Format

Every HTTP/3 frame has this structure:

```
┌─────────────┬─────────────┬─────────────────────┐
│ Type (var)  │ Length (var)│ Payload (Length B)  │
└─────────────┴─────────────┴─────────────────────┘
```

- **Type**: Varint — what kind of frame (HEADERS, DATA, etc.)
- **Length**: Varint — how many bytes of payload follow
- **Payload**: The frame data

### Frame Types We'll Implement

| Type | Value | Purpose |
|------|-------|---------|
| DATA | 0x00 | Request/response body |
| HEADERS | 0x01 | HTTP headers (method, path, status) |

(Other types like SETTINGS, GOAWAY exist but aren't needed for basic requests.)

---

## HTTP Semantics Refresher

### Request
```
Method: GET
Path: /hello
Headers: Host: example.com
Body: (empty for GET)
```

### Response
```
Status: 200
Headers: Content-Type: text/plain
Body: Hello World
```

These same semantics work across HTTP/1.1, HTTP/2, and HTTP/3 — only the encoding changes.

---

## Dependencies

This project builds on:
- `quic/` — QUIC streams and transport
- Varints — same encoding as protobuf!

---

## Files

```
http3/
├── README.md       — This file
├── http3.py        — Core implementation (frames, headers, build/parse)
├── client.py       — HTTP/3 client (uses quic/quic_client.py)
└── server.py       — HTTP/3 server (uses TUN interface)
```

---

## Integration Plan

### Architecture

```
┌─────────────────────────────────────┐
│  http3/client.py                    │  ← HTTP/3 client
│  - build_request()                  │
│  - parse_response()                 │
├─────────────────────────────────────┤
│  quic/sender.py                     │  ← QUIC client transport
│  - do_handshake() / do_0rtt()       │
│  - send_data()                      │
│  - Uses regular Python sockets      │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  http3/server.py                    │  ← HTTP/3 server
│  - parse_request()                  │
│  - build_response()                 │
├─────────────────────────────────────┤
│  quic/udp_multiplexer.py            │  ← QUIC server transport
│  - TUN interface (requires sudo)    │
│  - Handles multiple streams         │
└─────────────────────────────────────┘
```

### Key QUIC Functions to Reuse

From `quic/sender.py` (client):
```python
sock = socket.socket(AF_INET, SOCK_DGRAM)
aes_key = do_handshake(sock)       # Full handshake
aes_key, pub = do_0rtt(sock)       # 0-RTT (cached key)
send_data(sock, stream_id, offset, data)
```

From `quic/udp_multiplexer.py` (server):
- Receives packets via TUN interface
- Decrypts and routes to streams
- Needs modification to handle HTTP/3 frames

### What We Need to Add

1. **Receive response data** — currently only receives ACKs
2. **HTTP/3 framing** — wrap/unwrap our frames over QUIC streams
3. **Request routing** — server routes paths to handlers

---

## Historical Context

| Year | Event |
|------|-------|
| 1991 | HTTP/0.9 — Tim Berners-Lee's original, no headers |
| 1996 | HTTP/1.0 — Headers, status codes |
| 1997 | HTTP/1.1 — Keep-alive, Host header |
| 2015 | HTTP/2 — Binary, multiplexed over TCP |
| 2022 | HTTP/3 — QUIC transport (RFC 9114) |

---

## Current Status

**✅ Complete!**

### Functions

| Function | Purpose |
|----------|---------|
| `encode_frame` | Wrap payload in HTTP/3 frame |
| `decode_frame` | Read frame from bytes |
| `encode_headers` | Dict → header bytes |
| `decode_headers` | Header bytes → dict |
| `build_request` | Create GET/POST request |
| `build_response` | Create response with status + body |
| `parse_request` | Extract method + path |
| `parse_response` | Extract status + body |

### Running

**Terminal 1 (Server):**
```bash
cd http3
sudo python server.py
# Configure TUN interface as prompted
```

**Terminal 2 (Client):**
```bash
cd http3
python -c "from client import request; print(request('192.168.100.2', 9000, 'GET', '/Ahoy'))"
# Output: (200, b'Hello World')
```
