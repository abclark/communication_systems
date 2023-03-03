# TCP/IP Stack: User-Space Networking from Scratch

**Handle raw IP packets without the operating system.**

A from-scratch implementation of the TCP/IP protocol suite in Python. Bypasses the kernel's networking stack to manually parse IPv4 headers, respond to pings, and complete TCP handshakes — all in user-space code.

https://github.com/user-attachments/assets/9326d3ba-b905-4b3a-8054-f8e5aa8022d7

---

## Quick Demo

```bash
cd tcp_ip_stack
sudo python stack.py
```

In another terminal:
```bash
# Configure the virtual interface
sudo ifconfig utun4 10.0.0.1 10.0.0.1 netmask 255.255.255.0 up

# Test ICMP (ping)
ping -c 1 10.0.0.1

# Test TCP (chat)
nc 10.0.0.1 8000
```

**Sample Output:**
```
--- PARSED IP HEADER ---
IPv4 (len=44 bytes) from 10.0.0.1 to 10.0.0.1 [Proto=6 TTL=64]
--- PARSED TCP HEADER ---
TCP(Src=52431, Dst=8000, Seq=1234567890, Ack=0, Flags=[SYN], Win=65535)
   >>> Received SYN. Sending SYN-ACK...
   >>> Received ACK. Connection ESTABLISHED.
   >>> Received 12 bytes. Sending ACK...
   Message: Ahoy Matey
   Reply: Ahoy!
```

---

## What is User-Space Networking?

Normally when you run `ping` or `nc`, your OS kernel handles all the networking:

```
Your App → Kernel TCP/IP Stack → NIC Driver → Wire
```

The kernel parses headers, manages connections, computes checksums — you never see raw bytes.

**User-space networking** removes the kernel from the equation:

```
Your App → TUN Device → Your Code → TUN Device → Wire
```

A TUN (network **TUN**nel) device is a virtual network interface. Instead of connecting to physical hardware, packets go to a file descriptor your program can read and write.

**Why do this?**
- **Learning**: See exactly what's in each packet
- **Control**: Implement custom protocols (VPNs, game networking)
- **Performance**: Bypass kernel overhead (DPDK, high-frequency trading)

---

## The TUN Interface on macOS

macOS provides `utun` — a Layer 3 TUN interface. We create one using low-level kernel control sockets:

```python
# Open a system control socket
sock = socket.socket(PF_SYSTEM, socket.SOCK_DGRAM, SYSPROTO_CONTROL)

# Ask the kernel for the utun control ID
ctl_info = struct.pack('I96s', 0, b"com.apple.net.utun_control")
ctl_info = ioctl(sock, CTLIOCGINFO, ctl_info)
ctl_id = struct.unpack('I96s', ctl_info)[0]

# Connect to create the interface
sock.connect((ctl_id, 0))  # Kernel assigns utun0, utun1, etc.
```

Now `sock.recv()` returns raw IP packets, and `sock.sendall()` injects them.

**Note:** macOS prepends a 4-byte protocol family header (2 = IPv4, 30 = IPv6) to each packet.

---

## IPv4 Header Structure

Every IP packet starts with a 20-byte header:

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
├─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┤
│Version│  IHL  │    ToS    │          Total Length             │
├─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┤
│         Identification        │Flags│    Fragment Offset      │
├─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┤
│    TTL    │    Protocol   │         Header Checksum           │
├─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┤
│                       Source IP Address                       │
├─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┤
│                    Destination IP Address                     │
└─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┘
```

Key fields:
- **IHL** (Internet Header Length): Header size in 32-bit words (usually 5 = 20 bytes)
- **Protocol**: What comes next (1=ICMP, 6=TCP, 17=UDP)
- **TTL**: Hops remaining before packet is discarded

Parsing with `struct.unpack`:
```python
header = struct.unpack('!BBHHHBBH4s4s', packet[:20])
version = header[0] >> 4       # High nibble
ihl = header[0] & 0x0F         # Low nibble
protocol = header[6]
src_ip = socket.inet_ntoa(header[8])
dst_ip = socket.inet_ntoa(header[9])
```

---

## The Internet Checksum (RFC 1071)

IP, ICMP, UDP, and TCP all use the same checksum algorithm — the **one's complement sum**.

### The Algorithm

1. **Sum** all 16-bit words in the data
2. **Fold** any overflow back into the lower 16 bits
3. **Invert** all bits (one's complement)

```python
def calculate_checksum(data):
    # Pad to even length
    if len(data) % 2 == 1:
        data += b'\x00'

    # Sum 16-bit words
    s = 0
    for i in range(0, len(data), 2):
        word = (data[i] << 8) + data[i+1]
        s += word

    # Fold carries
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)

    # Invert
    return ~s & 0xFFFF
```

### Why This Works

The checksum is the **additive inverse** in mod-(2¹⁶-1) arithmetic:

```
Sum(Data) + Checksum ≡ 0 (mod 65535)
```

When the receiver sums data + checksum, the result is 0xFFFF ("negative zero") if valid.

### Why This Design?

- **Endian-independent**: Math works regardless of byte order
- **Fast**: Simple addition, no polynomial division (unlike CRC)
- **Incremental**: Can update without recalculating everything

---

## ICMP: The Ping Protocol

ICMP (Internet Control Message Protocol) handles network diagnostics. The `ping` command sends an **Echo Request** (type 8) and expects an **Echo Reply** (type 0).

```
┌────────────┬────────────┬─────────────────────────┐
│  Type (8)  │  Code (0)  │        Checksum         │
├────────────┴────────────┼─────────────────────────┤
│       Identifier        │    Sequence Number      │
├─────────────────────────┴─────────────────────────┤
│                     Payload                       │
└───────────────────────────────────────────────────┘
```

Responding to a ping:
```python
if icmp.type == 8:  # Echo Request
    reply = ICMPMessage(
        type=0,  # Echo Reply
        code=0,
        identifier=icmp.identifier,
        sequence_number=icmp.sequence_number,
        payload=icmp.payload
    )
    send(reply)
```

---

## UDP: Connectionless Datagrams

UDP adds ports for multiplexing but no reliability — fire and forget.

```
┌─────────────────────────┬─────────────────────────┐
│      Source Port        │    Destination Port     │
├─────────────────────────┼─────────────────────────┤
│        Length           │        Checksum         │
├─────────────────────────┴─────────────────────────┤
│                       Data                        │
└───────────────────────────────────────────────────┘
```

UDP checksum includes a **pseudo-header** (IPs + protocol + length) to catch misrouted packets:

```python
pseudo_header = struct.pack('!4s4sBBH',
    src_ip_bytes, dst_ip_bytes,
    0, 17,  # Reserved, Protocol (UDP)
    udp_length
)
checksum = calculate_checksum(pseudo_header + udp_packet)
```

---

## TCP: The Reliable Stream

TCP provides reliable, ordered delivery through sequence numbers, acknowledgments, and a state machine.

### The 3-Way Handshake

```
Client                          Server
  │                               │
  │──────── SYN (seq=x) ────────▶│
  │                               │
  │◀─── SYN-ACK (seq=y, ack=x+1) ─│
  │                               │
  │──────── ACK (ack=y+1) ───────▶│
  │                               │
  │        ESTABLISHED            │
```

1. **SYN**: "I want to connect, starting at sequence x"
2. **SYN-ACK**: "Acknowledged. I'm starting at sequence y"
3. **ACK**: "Got it. Let's talk."

### TCP Header

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
├─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┤
│          Source Port          │       Destination Port        │
├─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┤
│                        Sequence Number                        │
├─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┤
│                    Acknowledgment Number                      │
├─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┤
│ Offset│ Rsvd  │C│E│U│A│P│R│S│F│            Window             │
├─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┤
│           Checksum            │         Urgent Pointer        │
└─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┘
```

Flags: **S**YN, **A**CK, **F**IN, **R**ST, **P**SH, **U**RG

### The State Machine

```
                    ┌─────────┐
                    │  LISTEN │
                    └────┬────┘
                         │ recv SYN, send SYN-ACK
                         ▼
                  ┌──────────────┐
                  │ SYN_RECEIVED │
                  └──────┬───────┘
                         │ recv ACK
                         ▼
                  ┌─────────────┐
                  │ ESTABLISHED │◀──── Data transfer
                  └──────┬──────┘
                         │ recv FIN, send ACK+FIN
                         ▼
                   ┌──────────┐
                   │ LAST_ACK │
                   └────┬─────┘
                        │ recv ACK
                        ▼
                    ┌────────┐
                    │ CLOSED │
                    └────────┘
```

### Connection Teardown

Either side can initiate closing with FIN:

```
Client                          Server
  │                               │
  │──────── FIN ────────────────▶│
  │                               │
  │◀─────── ACK + FIN ───────────│
  │                               │
  │──────── ACK ────────────────▶│
  │                               │
  │        CLOSED                 │
```

---

## Project Architecture

```
tcp_ip_stack/
├── stack.py          # TunDevice + main loop
├── packet_headers.py # IPHeader, TCPHeader, UDPHeader, ICMPMessage
├── protocols.py      # Constants (PROTO_TCP, TCP_FLAG_SYN, etc.)
├── utils.py          # RFC 1071 checksum
├── icmp_handler.py   # Ping request/reply
├── udp_handler.py    # UDP echo (reverses payload)
└── tcp_handler.py    # TCP state machine + echo server
```

**Data flow:**
```
TUN recv → IPHeader.from_bytes → protocol dispatch → Handler
                                                      │
TUN send ← IPHeader.to_bytes ← TCPHeader.to_bytes ←───┘
```

---

## What's Implemented

| Protocol | Feature | Status |
|----------|---------|--------|
| IPv4 | Header parsing | ✅ |
| IPv4 | Header construction + checksum | ✅ |
| ICMP | Echo Request/Reply (ping) | ✅ |
| UDP | Parse + Echo server | ✅ |
| TCP | 3-way handshake | ✅ |
| TCP | Data transfer + ACK | ✅ |
| TCP | Connection teardown (FIN) | ✅ |
| TCP | RST for unknown connections | ✅ |

---

## Known Limitations

- **No incoming checksum verification**: Packets are trusted without validation
- **No sequence wraparound**: Transfers >4GB will overflow 32-bit sequence numbers
- **No retransmission**: If our reply is lost, we don't resend
- **Fixed window size**: No flow control (always advertises 65535)
- **IPv6 ignored**: Only handles IPv4 (protocol family 2)

---

## Dependencies

- Python 3.x
- macOS (uses `utun` interface)
- Root privileges (`sudo`)

---

## Further Reading

- [RFC 791](https://tools.ietf.org/html/rfc791) — Internet Protocol (IPv4)
- [RFC 793](https://tools.ietf.org/html/rfc793) — Transmission Control Protocol
- [RFC 1071](https://tools.ietf.org/html/rfc1071) — Computing the Internet Checksum
- [RFC 792](https://tools.ietf.org/html/rfc792) — Internet Control Message Protocol
