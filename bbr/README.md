# BBR: Building Congestion Control from Scratch

This project implements BBR (Bottleneck Bandwidth and Round-trip propagation time), Google's congestion control algorithm. We'll extend our QUIC implementation to send at the optimal rate.

## Demo

https://github.com/user-attachments/assets/2ab48189-1617-44f8-8f02-9160cbe77607

BBR discovering network capacity: STARTUP (exponential growth) → DRAIN (empty queues) → CRUISE (steady state). The cwnd adapts to the bottleneck bandwidth while keeping RTT close to RTprop.

---

## The Question

Our QUIC sender blasts packets as fast as possible. **How fast should we actually send?**

---

## The Core Insight

Every network path has two properties:

```
Sender ───────────────────────────────────────► Receiver
           │                           │
           │   Bottleneck Bandwidth    │
           │   (slowest link)          │
           │                           │
           │   Round-trip Prop Time    │
           │   (physical delay)        │
           └───────────────────────────┘
```

**Bottleneck Bandwidth (BtlBw):** The slowest link determines max throughput.

**Round-trip Propagation Time (RTprop):** The delay when queues are empty.

If you know these two things, you know exactly how fast to send.

---

## The Bandwidth-Delay Product

```
BDP = BtlBw × RTprop
```

This is the amount of data that "fits in the pipe" — traveling from sender to receiver and back — without any queuing.

**Example:**
- BtlBw = 10 Mbps (1.25 MB/s)
- RTprop = 40 ms
- BDP = 1.25 MB/s × 0.04s = 50 KB

You can have **at most 50 KB in flight** before packets start queuing.

---

## Why Two Controls?

### Pacing (Rate)

How fast you push packets out.

```
Without pacing: [pkt][pkt][pkt][pkt][pkt]........waiting........
                ↑ burst fills buffers

With pacing:    [pkt]...[pkt]...[pkt]...[pkt]...[pkt]...[pkt]...
                ↑ smooth flow, buffers stay empty
```

### Window (BDP Limit)

Maximum unacknowledged data allowed.

```
inflight = bytes_sent - bytes_acked

if inflight >= BDP:
    STOP sending, wait for ACKs
else:
    OK to send more
```

### Why You Need Both

**Pacing without window:** If ACKs stop coming (link dies?), you keep sending. Overflow.

**Window without pacing:** You can send BDP bytes, but you blast them all at once. Bursts fill buffers.

**Together:** Window limits how much. Pacing spreads it smoothly.

---

## Self-Regulating: Bandwidth Drops

If bottleneck bandwidth drops, ACKs come back slower:

```
Sending at 10 Mbps...
Hit BDP limit (50 KB in flight)
Wait for ACKs...
ACKs coming slower (new bottleneck!)
Can only send when ACKs arrive
Naturally slow down
Measure new bandwidth from ACK rate
```

**Automatic.** You can't send without ACKs, so you match the new rate.

---

## Probing: Bandwidth Increases

If bottleneck bandwidth increases, you don't notice automatically:

```
Before: Sending at 5 Mbps, pipe can carry 5 Mbps
After:  Sending at 5 Mbps, pipe can carry 10 Mbps
        ↑ still sending at old rate — can't see the extra capacity!
```

**Must actively probe.** Send faster, see what happens:

```
Probe at 1.25× current rate:
├── RTT stays flat? → More bandwidth available. Keep it!
└── RTT rises? → Queue building. Back off.
```

---

## The Signals

| Observation | Meaning | Action |
|-------------|---------|--------|
| Delivery rate up, RTT flat | More bandwidth | Increase estimate |
| Delivery rate same, RTT rising | Sending too fast | Back off |
| ACKs slow down | Bandwidth dropped | Automatic slowdown |

**RTT rising = early warning.** React before loss occurs.

---

## Measuring

### Bandwidth (BtlBw)

Track delivery rate for each ACK:

```
delivery_rate = bytes_acked / time_to_deliver

BtlBw = max(recent delivery_rate samples)
```

Maximum = true bandwidth (lower samples had queuing delay).

### RTT (RTprop)

Track minimum RTT:

```
rtt = now - send_time_of_acked_packet

RTprop = min(recent rtt samples)
```

Minimum = true propagation delay (higher samples had queuing).

---

## The BBR State Machine

```
STARTUP ──► DRAIN ──► CRUISE ◄──► PROBE
                        │           │
                        └► PROBE_RTT◄┘
```

**STARTUP:** Increase cwnd until RTT rises above 1.25× RTprop. Find initial capacity.

**DRAIN:** Decrease cwnd until RTT returns to ~1.1× RTprop. Empty queues.

**CRUISE:** Hold cwnd steady for 5 seconds. Stable operation.

**PROBE:** Increase cwnd to discover new bandwidth. If RTT rises → DRAIN.

**PROBE_RTT:** Every ~10 seconds, reduce cwnd to minimum to measure fresh RTprop. Handles route changes where propagation delay drops.

**DRAIN timeout:** If stuck draining >5 seconds, reset RTprop to current RTT. Handles route changes where propagation delay increases.

---

## Build Plan

We'll extend our QUIC implementation step by step:

### Step 1: Track Packets

Record send time for each packet. On ACK, calculate delivery rate and RTT.

### Step 2: Estimate BtlBw and RTprop

Track max delivery rate and min RTT over recent samples.

### Step 3: Calculate BDP

```
BDP = BtlBw × RTprop
```

Limit in-flight data to BDP.

### Step 4: Implement Pacing

Instead of sending bursts, send packets at steady intervals:

```
pacing_interval = packet_size / pacing_rate
```

### Step 5: Add Probing

Periodically send faster (1.25×) to discover new bandwidth. Back off if RTT rises.

### Step 6: State Machine

Implement startup (exponential), drain, probe_bw (cycling), probe_rtt.

### Step 7: Test

Simulate varying network conditions. Observe adaptation.

---

## Testing Setup (macOS)

The TUN loopback has no real bottleneck — packets flow through memory instantly. To test congestion control, we need to simulate a real network with limited bandwidth and delay.

### Traffic Shaping with dummynet

macOS includes `dnctl` (dummynet) for traffic shaping. Create a pipe that limits bandwidth and adds delay:

```bash
# Create a pipe: 1 Mbit/s bandwidth, 20ms delay each direction, queue of 100 packets
sudo dnctl pipe 1 config bw 1Mbit/s delay 20ms queue 100
```

- **bw 1Mbit/s**: Bottleneck bandwidth (125 KB/s)
- **delay 20ms**: One-way delay (RTT will be ~40ms minimum)
- **queue 100**: Buffer size in packets (max 100 on macOS)

### Route Traffic Through the Pipe

Use `pfctl` to route TUN interface traffic through the pipe:

```bash
# Find your TUN interface (e.g., utun6)
ifconfig | grep utun

# Apply rules (replace utun6 with your interface)
echo "dummynet out on utun6 all pipe 1
dummynet in on utun6 all pipe 1" | sudo pfctl -f -

# Enable pf if not already enabled
sudo pfctl -e
```

### Verify Setup

```bash
# Check pipe configuration
sudo dnctl list

# Check pf rules
sudo pfctl -s all | grep dummynet
```

### Expected Behavior

With 1 Mbit/s, 20ms delay, 1KB packets:
- **RTprop** ≈ 40-50ms (round-trip propagation)
- **BDP** = 125 KB/s × 0.04s ≈ 5 KB ≈ 5 packets
- **cwnd should stabilize around 5-6** before RTT starts rising

### Cleanup

```bash
# Remove pipe
sudo dnctl flush

# Disable pf rules
sudo pfctl -F all
```

---

## Project Status

- [x] Step 1: Track packets (send time, RTT)
- [x] Step 2: Estimate RTprop (minimum RTT)
- [x] Step 3: Limit in-flight based on RTT (stop when RTT > 1.25× RTprop)
- [x] Step 4: Implement pacing (spread packets over RTT)
- [x] Step 5: State machine (STARTUP → DRAIN → CRUISE → PROBE → PROBE_RTT)
- [x] Step 6: Adaptive RTprop (handle both increases and decreases)
- [x] Step 7: Test with varying network conditions (dummynet)
- [ ] Optional: Measure BtlBw (delivery rate) for calculated BDP

**Note:** We discover BDP empirically by probing until RTT rises, rather than calculating it from BtlBw × RTprop. This works well in practice.

---

## Key Formulas

```
BDP = BtlBw × RTprop

pacing_rate = pacing_gain × BtlBw

inflight_limit = cwnd_gain × BDP

delivery_rate = bytes_delivered / delivery_time

BtlBw = max(delivery_rate samples)

RTprop = min(rtt samples)
```

---

## References

- [BBR: Congestion-Based Congestion Control](https://research.google/pubs/pub45646/) — Google's paper
- [Van Jacobson's 1988 Paper](https://ee.lbl.gov/papers/congavoid.pdf) — Original congestion control
- [BBR v2 IETF Draft](https://datatracker.ietf.org/doc/html/draft-cardwell-iccrg-bbr-congestion-control)

---

## Files

```
bbr/
  __init__.py          — Package exports (BBR, CongestionController, CongestionDecision)
  bbr.py               — BBR implementation (state machine, RTprop tracking, pacing)
  README.md            — This file

quic/
  sender.py            — QUIC client using BBR for congestion control
  udp_multiplexer.py   — QUIC server (echoes ACKs)
```

## Usage

```python
from bbr import BBR

controller = BBR()

# On each ACK, record RTT
controller.on_ack(rtt)

# Periodically get send decision
decision = controller.update(time.time())

# Use decision
if inflight < decision.cwnd:
    if time_since_last_send >= decision.pacing_interval:
        send_packet()
```
