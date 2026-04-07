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
