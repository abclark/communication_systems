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

- [ ] Step 1: TCP Multiplexing (feel head-of-line blocking)
- [ ] Step 2: UDP Multiplexing (solve head-of-line blocking)
- [ ] Step 3: Reliability Layer (ACKs, retransmission)
- [ ] Step 4: Merged Handshake (reduce latency)
- [ ] Step 5: Connection IDs (connection migration)
- [ ] Step 6: Encryption (prevent ossification)
- [ ] Step 7: QUIC Wire Format (RFC 9000)
- [ ] Step 8: Integration with custom stack
