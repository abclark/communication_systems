# QUIC: Building "TCP 2.0" from Scratch

This project implements the QUIC protocol from the ground up. QUIC is the transport protocol underlying HTTP/3 and now carries over 30% of internet traffic.

---

## Why QUIC Exists

### The Problem with TCP

TCP was designed in 1974. It works, but has fundamental limitations:

1. **Head-of-Line Blocking**: If packet 3 of 10 is lost, packets 4-10 must wait even if they arrived. One lost packet stalls everything.

2. **Slow Handshake**: TCP needs 1-2 round trips before data flows (SYN → SYN-ACK → ACK, then TLS handshake on top).

3. **Ossification**: TCP is in the kernel. Changing it requires OS updates across billions of devices. Takes decades.

4. **No Built-in Encryption**: TLS is bolted on top, adding more round trips.

### QUIC's Solution

Google said: "What if we rebuilt TCP's reliability... on top of UDP?"

```
Traditional:                    QUIC:
┌─────────────┐                ┌─────────────┐
│    HTTP/2   │                │   HTTP/3    │
├─────────────┤                ├─────────────┤
│     TLS     │                │    QUIC     │ ← Reliability + Encryption
├─────────────┤                ├─────────────┤    combined, in user-space
│     TCP     │ (kernel)       │     UDP     │ (kernel just passes packets)
├─────────────┤                ├─────────────┤
│     IP      │                │     IP      │
└─────────────┘                └─────────────┘
```

---

## Key Features

| Feature | TCP | QUIC |
|---------|-----|------|
| **Handshake** | 2-3 RTT (TCP + TLS) | 1 RTT (0-RTT for repeat connections) |
| **Encryption** | Optional (TLS on top) | Mandatory, built-in |
| **Streams** | One stream per connection | Multiple streams, independent |
| **Head-of-Line** | Blocked | Each stream independent |
| **Connection Migration** | IP change = new connection | Connection ID survives IP change |
| **Updatable** | Kernel (slow) | User-space (ship with app) |

---

## How It Works

### Connection IDs

Instead of identifying connections by (IP, port), QUIC uses a random ID. Phone switches from WiFi to cellular? Same connection continues.

### Streams

One QUIC connection carries multiple independent streams. Stream 1 losing a packet doesn't block Stream 2.

### Packets and Frames

Each QUIC packet contains frames (like "stream data", "ack", "crypto"). All encrypted.

### Built-in TLS 1.3

The handshake negotiates encryption AND connection parameters together.

```
Traditional TCP + TLS:
  Client → Server: SYN
  Server → Client: SYN-ACK
  Client → Server: ACK
  Client → Server: TLS ClientHello
  Server → Client: TLS ServerHello, Certificate, Finished
  Client → Server: TLS Finished
  Client → Server: HTTP Request        ← Finally! (3 RTT)

QUIC:
  Client → Server: Initial (ClientHello + Stream 0 data)
  Server → Client: Initial (ServerHello) + Handshake + 1-RTT data
  Client → Server: HTTP Request        ← Done! (1 RTT)
```

---

## Learning Journey: Rediscovering QUIC

We follow the historical development path - experiencing each problem, then inventing the solution. This mirrors how Google actually built QUIC.

```
Experience problem → Invent solution → Repeat
        ↓                   ↓
   "This sucks"      "What if we..."
```

### Step 1: Feel Head-of-Line Blocking

**The year is 2009.** HTTP/1.1 opens 100 TCP connections per page. Wasteful. You invent multiplexing - many streams over ONE connection.

Build a TCP multiplexer (mini-SPDY):
- 3 streams over one TCP connection
- Simulate delay/loss on stream 2
- Watch streams 1 and 3 stall

*Feel* why TCP multiplexing is broken. TCP's ordered delivery guarantee becomes the enemy.

### Step 2: "What if UDP?"

**The year is 2012.** You can't fix TCP (kernel, middleboxes, billions of devices). What if you rebuilt reliability on UDP?

Rebuild the multiplexer over UDP:
- Same 3 streams, but UDP datagrams
- Loss on stream 2 doesn't block stream 1
- Each stream is independent

*Feel* the improvement. But now nothing is reliable...

### Step 3: Add Reliability

**You need ACKs.** UDP doesn't guarantee delivery. You must track what was sent and retransmit losses.

Build per-stream reliability:
- Sequence numbers per stream
- ACK frames
- Retransmission on timeout

*Feel* why QUIC needs its own reliability layer.

### Step 4: Handshake Latency

**Users complain about slow connections.** TCP handshake + crypto negotiation = 3 round trips before data.

Merge connection setup with crypto:
- Before: connect() then negotiate()
- After: connect+negotiate in one round trip
- Cache for repeat visitors: 0 round trips

*Feel* why QUIC merged the handshakes.

### Step 5: Connection Migration

**Mobile users disconnect constantly.** WiFi → cellular = IP change = TCP connection dies.

Add Connection IDs:
- Identify connection by random ID, not (IP, port)
- Simulate IP change mid-connection
- Connection survives

*Feel* why QUIC uses Connection IDs.

### Step 6: Encrypt Everything

**Middleboxes break your features.** They inspect TCP, modify it, enforce assumptions.

Encrypt the headers:
- Only Connection ID visible
- Everything else opaque
- Middleboxes can't interfere

*Feel* why QUIC encrypts almost everything.

### Step 7: Formalize into QUIC

Now we have the intuition. Refactor into proper QUIC wire format:

```
Varint encoding → Frame types → Packet headers → Full RFC 9000 compliance
```

### Step 8: Integration

Swap Python sockets for our custom stack:

```
┌─────────────────┐
│   QUIC logic    │  ← Built in Steps 1-7
├─────────────────┤
│  Our UDP        │  ← From tcp_ip_stack
├─────────────────┤
│  Our IP         │  ← From tcp_ip_stack
├─────────────────┤
│  Our TUN        │  ← From tcp_ip_stack
└─────────────────┘
```

---

## Key Concepts

### Variable-Length Integers

QUIC uses a clever encoding where the first 2 bits indicate the length:

```
00xxxxxx                 → 1 byte,  6-bit value (0-63)
01xxxxxx xxxxxxxx        → 2 bytes, 14-bit value (0-16383)
10xxxxxx (3 more bytes)  → 4 bytes, 30-bit value
11xxxxxx (7 more bytes)  → 8 bytes, 62-bit value
```

### Packet Number Spaces

QUIC has three separate packet number spaces:
- **Initial**: For connection setup
- **Handshake**: For TLS handshake completion
- **Application**: For actual data

### Encryption Levels

Each packet number space has its own encryption keys:
- Initial packets use keys derived from the connection ID (not secret!)
- Handshake packets use keys from TLS handshake
- Application packets use final TLS keys

---

## History: How QUIC Evolved

QUIC wasn't designed top-down. Each feature exists because engineers hit a wall.

### Chapter 1: SPDY (2009-2011)

HTTP/1.1 was slow - 100 resources = 100 TCP connections. Google built SPDY to multiplex requests over ONE connection. It worked.

### Chapter 2: Head-of-Line Blocking Returns (2011-2012)

SPDY made things worse on lossy networks. One lost packet now blocked ALL requests, not just one. TCP's ordered delivery guarantee became the enemy.

They couldn't fix TCP - it's in the kernel, middleboxes expect it, billions of devices would need updates.

### Chapter 3: "What if we used UDP?" (2012)

Jim Roskind's insight: rebuild reliability in userspace on UDP. Middleboxes ignore UDP. Kernel just passes bytes. They could iterate daily.

### Chapter 4: Independent Streams (2012-2013)

Each stream gets its own sequence numbers. Loss in stream 4 doesn't block stream 8. Head-of-line blocking: solved.

### Chapter 5: Merged Handshake (2013)

Why separate TCP handshake from TLS? Combine them. One round trip. Cache crypto params for returning visitors: zero round trips.

### Chapter 6: Connection IDs (2014)

Mobile users kept disconnecting when switching WiFi→cellular (IP changes). Solution: identify connections by ID, not IP tuple. Seamless migration.

### Chapter 7: Encrypt Everything (2014-2015)

Middleboxes kept breaking new features by inspecting/modifying packets. Solution: encrypt everything. If they can't see it, they can't break it.

### Chapter 8: IETF Standardization (2016-2021)

Google's QUIC worked but was proprietary. IETF standardized it as RFC 9000 (2021), with cleaner wire format and mandatory TLS 1.3.

### The Pattern

| Problem Encountered | Led To |
|---------------------|--------|
| 100 connections per page | Multiplexing (SPDY) |
| Multiplexing + loss = everything stalls | Independent streams |
| Can't change TCP kernel/middleboxes | Build on UDP |
| 3 RTT handshake | Merged crypto handshake |
| Mobile IP changes kill connections | Connection IDs |
| Middleboxes break new features | Encrypt everything |

---

## References

- [RFC 9000: QUIC Transport](https://www.rfc-editor.org/rfc/rfc9000.html)
- [RFC 9001: QUIC TLS](https://www.rfc-editor.org/rfc/rfc9001.html)
- [RFC 9002: QUIC Loss Detection](https://www.rfc-editor.org/rfc/rfc9002.html)
- [QUIC Working Group](https://quicwg.org/)

---

## Project Status

- [x] Step 1: TCP Multiplexing (feel head-of-line blocking)
- [x] Step 2: UDP Multiplexing (solve head-of-line blocking)
- [x] Step 3: Reliability Layer (ACKs, retransmission)
- [x] Step 4: Merged Handshake (reduce latency) — combined with Step 6
- [x] Step 5: Connection IDs (connection migration)
- [x] Step 6: Encryption (DH key exchange + AES-GCM)
- [ ] Step 7: QUIC Wire Format (RFC 9000)
- [ ] Step 8: Integration with custom stack

---

## How Diffie-Hellman Key Exchange Works

DH solves: "How do two parties agree on a secret key without anyone eavesdropping being able to figure it out?"

### The Setup

Two public parameters everyone knows:
- `p` = large prime (2048 bits in our code)
- `g` = generator (usually 2)

### The Exchange

```
Client picks secret: a (random integer)
Server picks secret: b (random integer)

Client computes: A = g^a mod p  → sends A to server
Server computes: B = g^b mod p  → sends B to client
```

### The Magic

```
Client computes: B^a mod p = (g^b)^a mod p = g^(ab) mod p
Server computes: A^b mod p = (g^a)^b mod p = g^(ab) mod p
                                              ↑
                                         SAME VALUE!
```

Both arrive at `g^(ab) mod p` — the shared secret. An eavesdropper sees `A` and `B` but can't compute `g^(ab)` without knowing `a` or `b`.

### Paint Analogy

```
Public: yellow paint (g, p)

Client: mixes in secret red (a)    → sends orange
Server: mixes in secret blue (b)   → sends green

Client: takes green, adds red      → brown
Server: takes orange, adds blue    → same brown!

Eavesdropper sees: yellow, orange, green
Can't unmix to find red or blue. Can't make brown.
```

### Why It's Secure

Finding `a` from `g^a mod p` is the **discrete logarithm problem** — computationally infeasible for large primes. More possibilities than atoms in the universe.

### From Shared Secret to Encryption

```
DH exchange → shared secret (2048-bit number)
     ↓
SHA256 hash → AES key (256 bits)
     ↓
AES-GCM → encrypt/decrypt actual data
```

DH establishes the key. AES does the fast symmetric encryption.

---

## Implementation Progress & Learnings

### What We Built

| Component | File | What It Does |
|-----------|------|--------------|
| TCP Multiplexer | `multiplexer.py` | Demonstrates head-of-line blocking |
| UDP Multiplexer | `udp_multiplexer.py` | Server with per-stream delivery, no blocking |
| Sender | `sender.py` | Client with retransmission and migration test |
| Crypto | `crypto.py` | DH key exchange + AES-GCM encryption |

### Key Learnings

**Why UDP over TCP?**
TCP is in the kernel. You can't change how it identifies connections (4-tuple) or handles loss (ordered delivery). UDP just delivers bytes — you build whatever semantics you want on top.

**Connection ID vs IP/Port:**
TCP: connection = (src_ip, src_port, dst_ip, dst_port). IP changes = dead connection.
QUIC: connection = random ID in packet payload. IP can change freely.

**The Trust Problem (CAs):**
DH gives secrecy but not authentication. You don't know *who* you're talking to. Real QUIC uses TLS certificates signed by Certificate Authorities. The whole internet trusts ~100 CAs not to misbehave. Certificate Transparency logs provide accountability.

**Why Encrypt Everything?**
Middleboxes (firewalls, NATs, corporate proxies) inspect and modify TCP packets. They break new features by enforcing old assumptions. If everything is encrypted, they can't interfere. Only the Connection ID is visible.

**0-RTT Tradeoff:**
Caching crypto params allows zero round-trip connections for returning clients. But 0-RTT data can be replayed by attackers. Only safe for idempotent operations (GET, not POST).

### Packet Format Evolution

```
Step 1 (TCP): Kernel handles everything

Step 2 (UDP): [stream_id 1B][data...]

Step 3 (+ reliability): [stream_id 1B][seq 2B][data...]

Step 4-6 (+ crypto): [type 1B][DH public 256B]  (handshake)
                     [type 1B][stream_id 1B][seq 2B][encrypted...]  (data)

Step 5 (+ conn ID): [type 1B][conn_id 8B][stream_id 1B][seq 2B][encrypted...]
```

Each addition solved a specific problem we felt firsthand.

---

## Files

- **multiplexer.py** — TCP multiplexer demonstrating head-of-line blocking.
  Three TCP connections (ports 9001-9003) mapped to streams 1-3, sharing a
  global sequence. Stream 2 is artificially delayed. Shows how one slow
  stream blocks all others. This is "the problem" that QUIC solves.

- **udp_multiplexer.py** — UDP server with Connection ID support. Looks up
  connections by ID (not IP/port), enabling connection migration. Handles
  INIT/ACCEPT handshake, encrypts/decrypts data with per-connection AES keys.

- **sender.py** — UDP client that performs DH handshake, sends encrypted data,
  handles ACKs and retransmission. Includes migration test (closes socket,
  opens new one, continues sending with same Connection ID).

- **crypto.py** — Diffie-Hellman key exchange (2048-bit MODP group from RFC 3526)
  and AES-GCM encryption. Functions: generate_private_key, compute_public_key,
  compute_shared_secret, derive_aes_key, encrypt, decrypt.
