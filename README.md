# Communication Systems from Scratch

This repo is a collection of small projects that rebuild pieces of the internet in plain code.

The goal is to understand how networking works by implementing the layers yourself:
- how bits move over a medium
- how packets are routed
- how reliable connections are built
- how modern application protocols sit on top

Instead of treating the internet as a black box, these projects open it up one layer at a time.

## What Is Here

Each folder focuses on one protocol or one part of the stack.

## Completed Projects

### [tcp_ip_stack](./tcp_ip_stack/)
A basic TCP/IP stack built over a TUN interface.

What it covers:
- parsing and building IP packets
- ICMP ping support
- a UDP echo server
- TCP connection setup, data transfer, and shutdown

### [quic](./quic/)
A from-scratch implementation of the ideas behind QUIC.

What it covers:
- packet formats
- variable-length integers
- streams and flow control
- connection IDs and migration
- 0-RTT style handshake ideas

### [bbr](./bbr/)
An implementation of Google's BBR congestion-control algorithm.

What it covers:
- bandwidth estimation
- round-trip propagation tracking
- pacing
- congestion-window control

### [protobuf](./protobuf/)
A simple implementation of Protocol Buffers encoding.

What it covers:
- varints
- wire types
- field tags
- binary message encode/decode

### [bgp](./bgp/)
A project for understanding how internet routes are chosen.

What it covers:
- the BGP state machine
- route/path selection
- timers and protocol flow

### [audio_modem](./audio_modem/)
A physical-layer style project that sends data over sound.

What it covers:
- frequency-shift keying
- framing and synchronization
- CRC checking
- cross-computer transmission through audio

### [http3](./http3/)
An HTTP/3 layer built on top of the QUIC work.

What it covers:
- HTTP/3 frame encoding
- headers and body framing
- request/response parsing
- client/server integration over QUIC

## In Progress

### [virtual_router](./virtual_router/)
A project to connect routing and packet forwarding into a fuller router simulation.

Current direction:
- routers exchanging BGP messages
- route advertisement and selection
- end-to-end routing demo

## Planned

### [grpc](./grpc/)
A future RPC project built on top of the Protobuf and HTTP/3 work.

Likely scope:
- service definitions
- unary calls
- streaming calls

## Frontier / Stretch Projects

### [scion](./scion/)
A clean-slate internet architecture project.

Why it is interesting:
- path-aware networking
- stronger trust boundaries
- cryptographic path validation
- a more research-oriented design than standard internet protocols

## Other Folders

There are also supporting or side projects in the repo, including:
- `tcp_chat/`
- `google_technologies/`
- `voice_claude/`

## Why This Repo Exists

This repo is really about learning by reconstruction.

The basic pattern is:
1. pick a protocol
2. read the spec or the core ideas
3. implement the smallest useful version
4. use that implementation to understand what the protocol is actually doing

## Suggested Learning Order

If you want to read the repo in a sensible order, start here:

1. `audio_modem`  
   Start at the bottom of the stack: how signals can carry information.

2. `tcp_ip_stack`  
   Learn how packets move, how hosts talk, and how TCP/UDP differ.

3. `bgp`  
   Learn how route decisions are made across networks.

4. `protobuf`  
   Learn a compact binary format for structured data.

5. `quic`  
   Learn how a modern transport protocol builds reliability on top of UDP.

6. `http3`  
   See how application protocols sit on top of modern transport.

7. `grpc`  
   Natural next step once Protobuf and HTTP/3 are both in place.

8. `scion`  
   A more experimental "what could the internet look like instead?" project.

## Simple Map Of The Stack

You can think of the repo like this:

- `audio_modem` -> physical signaling
- `tcp_ip_stack` -> packets and transport basics
- `bgp` -> routing decisions
- `protobuf` -> binary message format
- `quic` -> modern reliable transport over UDP
- `http3` -> web protocol on top of QUIC
- `grpc` -> structured RPC on top of HTTP/3 and Protobuf
- `scion` -> alternative future-network architecture

## References

Useful background:

- *TCP/IP Illustrated* by Stevens
- *Computer Networking: A Top-Down Approach* by Kurose and Ross
- *High Performance Browser Networking* by Ilya Grigorik

Useful RFCs:

- RFC 793 for TCP
- RFC 9000 for QUIC
- RFC 4271 for BGP
