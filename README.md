# Communication Systems from Scratch

The entire internet networking stack, built from scratch in Python.

1. **tcp_chat** — Secure chat (TCP → TLS → E2EE with RSA + AES-GCM)
2. **tcp_ip_stack** — User-space networking (TUN → IPv4 → ICMP → UDP → TCP)
3. **quic** — QUIC from scratch (UDP → reliability → DH → 0-RTT → migration → frames)
4. **protobuf** — Protocol Buffers wire format (varints → tags → encode/decode)
5. **http3** — HTTP/3 on top of QUIC (frames → headers → working client/server)
6. **bgp** — BGP finite state machine + path selection
7. **bbr** — Google's BBR congestion control
8. **audio_modem** — FSK modulation, FFT, CRC — TCP packets as sound through air
