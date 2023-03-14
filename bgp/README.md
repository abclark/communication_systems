# BGP: The Protocol That Runs the Internet

**Simulate how autonomous systems discover routes to each other.**

BGP (Border Gateway Protocol) is how the internet's backbone routers decide where to send traffic. When you visit google.com, BGP is why your packets know how to get from your ISP to Google's network. This project implements the two core BGP mechanisms: the session state machine and the path selection algorithm.

<!-- Demo video will go here -->

---

## Quick Demo

```bash
cd bgp

# Run the FSM demo (session establishment)
python main.py

# Run the path selection demo
python path_selection.py
```

**FSM Output:**
```
=== BGP FSM Demo ===

--- Starting peers ---
[10.0.0.1] Event: Start (state=IDLE)
[10.0.0.1] IDLE -> CONNECT
[10.0.0.2] Event: Start (state=IDLE)
[10.0.0.2] IDLE -> CONNECT

--- TCP connects ---
[10.0.0.1] CONNECT -> OPENSENT
[10.0.0.2] CONNECT -> OPENSENT

--- OPEN messages exchanged ---
[10.0.0.1] OPENSENT -> OPENCONFIRM
[10.0.0.2] OPENSENT -> OPENCONFIRM

--- KEEPALIVE messages exchanged ---
[10.0.0.1] OPENCONFIRM -> ESTABLISHED
[10.0.0.1] *** SESSION UP ***
```

---

## Why BGP Matters

The internet is not one network — it's ~70,000 **autonomous systems** (ASes) operated by ISPs, cloud providers, universities, and enterprises. BGP is how they share reachability information.

```
Your ISP (AS 7922) ←→ Tier-1 Provider (AS 3356) ←→ Google (AS 15169)
         ↑                                                ↑
         └──────── BGP sessions tell each AS ────────────┘
                   how to reach the others
```

When BGP breaks, parts of the internet go dark. The 2021 Facebook outage? BGP misconfiguration. Pakistan accidentally blocking YouTube worldwide in 2008? BGP hijacking.

---

## The BGP Finite State Machine

Two BGP routers (peers) establish a session through a 6-state machine defined in RFC 4271:

```
┌──────┐   Start    ┌─────────┐  TCP success  ┌──────────┐
│ IDLE │ ─────────▶ │ CONNECT │ ────────────▶ │ OPENSENT │
└──────┘            └─────────┘               └──────────┘
                         │                         │
                    TCP fails                 Valid OPEN
                         ▼                         ▼
                    ┌────────┐              ┌─────────────┐
                    │ ACTIVE │              │ OPENCONFIRM │
                    └────────┘              └─────────────┘
                         │                         │
                    TCP success               KEEPALIVE
                         │                         ▼
                         └───────────────▶ ┌─────────────┐
                                           │ ESTABLISHED │
                                           └─────────────┘
```

**States:**
- **IDLE**: Waiting to be started
- **CONNECT**: Attempting TCP connection (port 179)
- **ACTIVE**: TCP failed, retrying
- **OPENSENT**: TCP connected, sent OPEN message, waiting for peer's OPEN
- **OPENCONFIRM**: Received valid OPEN, waiting for KEEPALIVE
- **ESTABLISHED**: Session up, ready to exchange routes

**Timers:**
- **ConnectRetryTimer**: How long to wait before retrying TCP (default 120s)
- **HoldTimer**: If no KEEPALIVE/UPDATE received within this time, session dies (default 90s)

---

## The Path Selection Algorithm

When a router learns multiple routes to the same prefix, it must pick one. BGP uses a deterministic 8-step decision process:

| Step | Criterion | Prefer |
|------|-----------|--------|
| 1 | LOCAL_PREF | Higher (local policy) |
| 2 | AS_PATH | Locally originated |
| 3 | AS_PATH length | Shorter |
| 4 | ORIGIN | IGP > EGP > incomplete |
| 5 | MED | Lower (from same neighbor AS) |
| 6 | Source | eBGP over iBGP |
| 7 | IGP cost | Lower cost to next-hop |
| 8 | Router ID | Lowest (tie-breaker) |

**Example:** Four routes to 8.8.8.0/24:
```
[1] via AS 65001          LP=100, AS_PATH len=1, origin=IGP
[2] via AS 65002→65001    LP=100, AS_PATH len=2, origin=IGP
[3] via AS 65003          LP=90,  AS_PATH len=1, origin=IGP
[4] via AS 65004          LP=100, AS_PATH len=1, origin=EGP

Step 1 (LOCAL_PREF >= 100): 4 -> 3 routes  (eliminates [3])
Step 3 (AS_PATH len <= 1): 3 -> 2 routes   (eliminates [2])
Step 4 (ORIGIN = IGP): 2 -> 1 routes       (eliminates [4])

Winner: Route [1] via AS 65001
```

---

## eBGP vs iBGP

**eBGP** (external BGP): Sessions between different autonomous systems
- Peers are usually directly connected
- Routes learned have their AS_PATH prepended

**iBGP** (internal BGP): Sessions within the same AS
- Used to distribute external routes internally
- Requires full mesh or route reflectors (iBGP doesn't modify AS_PATH)

```
        AS 65001                         AS 65002
   ┌─────────────────┐              ┌─────────────────┐
   │  R1 ──iBGP── R2 │───eBGP─────▶│  R3 ──iBGP── R4 │
   │   │          │  │              │   │          │  │
   │   └──iBGP────┘  │              │   └──iBGP────┘  │
   └─────────────────┘              └─────────────────┘
```

---

## Project Structure

```
bgp/
├── src/
│   └── fsm.py           # BGPPeer class with state machine
├── main.py              # FSM demo scenarios
├── path_selection.py    # Best path algorithm demo
└── README.md
```

---

## What's Implemented

| Component | Feature | Status |
|-----------|---------|--------|
| FSM | 6 states (IDLE → ESTABLISHED) | ✅ |
| FSM | HoldTimer, ConnectRetryTimer | ✅ |
| FSM | Event-driven transitions | ✅ |
| Path Selection | All 8 decision steps | ✅ |
| Path Selection | LOCAL_PREF, AS_PATH, MED, ORIGIN | ✅ |

---

## Not Implemented

- Actual TCP connections (events are simulated)
- OPEN/UPDATE/NOTIFICATION message parsing
- Route advertisement and withdrawal
- Route reflectors, confederations
- MD5 authentication

---

## Further Reading

- [RFC 4271](https://tools.ietf.org/html/rfc4271) — BGP-4 Specification
- [BGP Table Statistics](https://bgp.potaroo.net/) — Live internet routing table size
- [BGP Stream](https://bgpstream.caida.org/) — Real-time BGP hijack detection
