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
- [x] Step 4: Merged Handshake + 0-RTT (reduce latency)
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

## How 0-RTT Works

### The Problem (2013)

QUIC has a 1-RTT handshake—already better than TCP+TLS (3 RTT). But Google measures everything.

The data showed: users make the same connections repeatedly. Open Gmail → close → open again. YouTube video → another video. Same servers, over and over.

The question: **If I talked to this server 10 seconds ago, why negotiate keys again?**

```
Every new connection pays the handshake tax:

User clicks link
    |
    |--- INIT --------→ Server
    |←-- ACCEPT -------|
    |                     ← 100ms (if server is far away)
    |--- DATA ---------→
    |←-- Response -----|
    |                     ← 100ms more

Total: 200ms before user sees anything
```

On mobile networks with 150ms RTT, users wait 300ms+ just for handshakes.

### The Solution

**First connection:** Full handshake. Client caches server's public key (g^b).

**Second connection:** Client already knows g^b. Send data immediately.

```
First visit:
  Client ←→ Server: INIT/ACCEPT (derive key K)
  Client saves: server's public key (g^b)

Second visit (0-RTT):
  Client → Server: DATA encrypted with new key
  Server → Client: Response

Total: 100ms. Half the latency.
```

### How It Works with DH

First connection:
```
Client: picks random a
Server: has long-term b

Client sends: g^a mod p
Server sends: g^b mod p

Both compute: g^(ab) mod p → shared secret → AES key
Client caches: g^b (server's public key)
```

Second connection (0-RTT):
```
Client: loads cached g^b
Client: picks NEW random a'
Client: computes (g^b)^a' = g^(a'b) → new shared secret → AES key
Client: encrypts data, sends g^a' + encrypted data in ONE packet

Server: receives g^a'
Server: computes (g^a')^b = g^(a'b) → same shared secret → same AES key
Server: decrypts immediately!
```

The server's keypair being **long-term** (not random per connection) is what makes this possible.

### The Replay Attack Problem

0-RTT has a vulnerability. An attacker doesn't need to break crypto—they just record and replay:

```
You (0-RTT): [g^a' + encrypted "transfer $100"]
    ↓
Attacker: *records this packet*
    ↓
Attacker: *replays it 50 times*
    ↓
Server: processes each one as valid!
```

The server can't tell replays from new requests—the crypto checks out every time.

**Why doesn't this happen with 1-RTT handshake?**

```
Connection 1: a=5, b=7 → key = g^35
Connection 2: a=9, b=7 → key = g^63 (different!)

Replay packet from Connection 1?
→ Wrong key, decryption fails, rejected
```

With 0-RTT, if you replay the same packet, the key derivation produces the same result.

### What's Safe for 0-RTT?

Only **idempotent operations**—requests that have the same effect if executed multiple times:

| Request | Safe? | Why |
|---------|-------|-----|
| `GET /homepage` | ✅ | Same result every time |
| `GET /search?q=cats` | ✅ | Same result every time |
| `POST /transfer` | ❌ | Side effects—money moves |
| `POST /login` | ❌ | Could create sessions |

The application layer decides what's safe to send as 0-RTT. QUIC just provides the mechanism.

### Real-World Protections

Production QUIC adds:
1. **Single-use tickets** — server issues a "session ticket" that can only be used once
2. **Time limits** — 0-RTT only valid for X seconds after last connection
3. **Strike registers** — server remembers recent 0-RTT packets to detect replays

We skip these for learning—the basic caching demonstrates the concept.

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

Step 4b (+ 0-RTT): [type 1B][conn_id 8B][client_public 256B][stream_id 1B][seq 2B][encrypted...]
                   ↑ Handshake + data in one packet!
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
  INIT/ACCEPT handshake and 0-RTT packets. Uses persistent DH keypair for
  0-RTT support. Encrypts/decrypts data with per-connection AES keys.

- **sender.py** — UDP client that performs DH handshake, sends encrypted data,
  handles ACKs and retransmission. Caches server's public key for 0-RTT on
  repeat connections. Includes migration test (closes socket, opens new one,
  continues sending with same Connection ID).

- **crypto.py** — Diffie-Hellman key exchange (2048-bit MODP group from RFC 3526)
  and AES-GCM encryption. Functions: generate_private_key, compute_public_key,
  compute_shared_secret, derive_aes_key, encrypt, decrypt.
