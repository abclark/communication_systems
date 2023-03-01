# Audio Modem: The Physical Layer from Scratch

**Transmit data as sound waves through the air.**

A software-defined acoustic modem that converts bytes to audio tones (FSK modulation), plays them through speakers, records through a microphone, and decodes back to bytes — including full TCP/IP packets.

https://github.com/abclark/communication_systems/releases/download/audio-modem-demo/demo.mov

---

## Quick Demo

```bash
cd audio_modem
source venv/bin/activate
pip install numpy sounddevice

# Test encode/decode (no audio needed)
python -c "from main import test_roundtrip; test_roundtrip()"

# Hear the modem tones (turn up speakers!)
python -c "from main import test_audio; test_audio()"

# Full loopback: encode → play → record → decode
python -c "from main import test_loopback; test_loopback()"

# TCP packet over audio (!!)
python -c "from main import test_tcp_syn; test_tcp_syn()"
```

**Sample Output (TCP over Audio):**
```
=== TCP SYN over Audio ===
1. Building TCP SYN packet...
   TCP header: 20 bytes
   IP header:  20 bytes
2. Transmitting via audio... (3.68 sec)
3. Decoding received audio...
   Status:   SUCCESS
4. Parsing received packet...
   IPv4 from 10.0.0.1 to 10.0.0.2 [Proto=TCP TTL=64]
   TCP(Src=12345, Dst=80, Seq=1000, Flags=[SYN])
```

---

## What is a Modem?

**MODEM = MOdulator-DEModulator**

A modem converts digital data (bits) into analog signals (modulation) and back (demodulation). The medium doesn't matter - phone lines, radio waves, or in our case, sound through air.

```
Computer A          Air (sound waves)     Computer B
[bits] → MODulate → [audio] → DEModulate → [bits]
         (speaker)            (microphone)
```

The dial-up modem screech of the 1990s? That WAS data - bits encoded as audio tones traveling over phone lines designed for human voice.

---

## The Physics of Sound

### How Do We Know Sound is a Wave?

1. **Interference**: Two speakers playing the same tone create "dead spots" where sound cancels out. Only waves can cancel - particles would just add up everywhere.

2. **Diffraction**: Sound bends around corners (you can hear someone you can't see). Waves bend around obstacles; particles travel in straight lines.

3. **Direct observation**: Watch a speaker cone move, see sand form patterns on a vibrating drum, look at a waveform on an oscilloscope.

### How Speakers Work

The chain from numbers to air pressure:

1. **Digital samples** (floats in memory) →
2. **DAC** (Digital-to-Analog Converter) outputs voltage →
3. **Amplifier** boosts the signal →
4. **Voice coil** (wire in magnetic field) experiences force →
5. **Cone** moves, pushing air →
6. **Pressure wave** propagates to your ear

The speaker cone literally traces out your waveform in physical space, 44,100 times per second.

---

## Frequency Shift Keying (FSK)

We encode bits as two different frequencies:

- **Bit 0**: 1000 Hz tone (lower pitch)
- **Bit 1**: 2000 Hz tone (higher pitch)

```
Binary: 1 0 1 0 1 0 1 0  (0xAA)
Audio:  ↑ ↓ ↑ ↓ ↑ ↓ ↑ ↓  (alternating high/low tones)
```

At 100 baud (bits per second), each bit lasts 10ms. In that time:
- 1000 Hz completes 10 cycles
- 2000 Hz completes 20 cycles

This difference is detectable by frequency analysis.

---

## Digital Sampling

### The Continuous-to-Discrete Problem

Sound is continuous; computers work with discrete samples. We capture snapshots of the wave:

```
Sample rate: 44,100 Hz = 44,100 samples per second
Bit duration: 10ms
Samples per bit: 44,100 × 0.01 = 441 samples
```

### Nyquist Theorem

To capture a frequency f, you need to sample at more than 2f. With 44,100 Hz sample rate, we can represent frequencies up to ~22,000 Hz (covering human hearing).

Below 2f, higher frequencies "alias" to look like lower ones - a wheel in video appearing to spin backwards.

---

## The Fourier Transform

### The Core Insight (Fourier, 1822)

Any signal can be decomposed into a sum of sine waves at different frequencies. Originally discovered to solve the heat equation, now fundamental to signal processing.

### What FFT Computes

The Fast Fourier Transform takes N time-domain samples and outputs N/2 frequency-domain coefficients:

```
Input:  [sample₀, sample₁, ..., sample₄₄₀]  (441 audio samples)
Output: [A₀, A₁, A₂, ..., A₂₂₀]              (amplitude at each frequency)
```

Each coefficient tells us "how much of this frequency is present in the signal."

### The Math

At each frequency k, we compute how well the signal correlates with a sine wave:

```
X[k] = Σ x[n] · e^(-i·2π·k·n/N)
```

Using Euler's formula (e^(iθ) = cos(θ) + i·sin(θ)), this multiplies the signal by sine and cosine waves and sums the products. When the signal contains that frequency, products reinforce. When it doesn't, they cancel.

### Frequency Resolution

With N samples over time T:
- **Resolution** = sample_rate / N = 1/T Hz per bin
- **Maximum frequency** = sample_rate / 2 (Nyquist)

For our 441 samples at 44,100 Hz:
- Duration: 10ms
- Resolution: 100 Hz per bin
- Bin 10 = 1000 Hz (our "0")
- Bin 20 = 2000 Hz (our "1")

### Why These Specific Bins?

The DFT only detects frequencies that complete a whole number of cycles in the observation window. In 10ms, a 100 Hz wave completes exactly 1 cycle - that's the finest distinction we can make.

---

## Decoding: From Audio Back to Bits

```python
def decode_bit(samples):
    spectrum = np.abs(np.fft.rfft(samples))

    freq_resolution = SAMPLE_RATE / len(samples)  # 100 Hz
    bin_0 = int(1000 / freq_resolution)  # bin 10
    bin_1 = int(2000 / freq_resolution)  # bin 20

    if spectrum[bin_1] > spectrum[bin_0]:
        return 1
    else:
        return 0
```

We ask: "Is the 2000 Hz coefficient bigger than the 1000 Hz coefficient?"

---

## Cross-Correlation: Finding the Signal

The receiver doesn't know exactly when the transmission starts. We use cross-correlation to find the signal in the recording.

**Cross-correlation** slides one signal over another, computing the dot product at each position:

```
correlation[k] = Σ recording[k+i] × pattern[i]
```

When the pattern aligns with itself in the recording, all products reinforce → maximum correlation. The position of this maximum tells us where the signal starts.

```python
def find_signal_offset(sent, recorded):
    correlation = np.correlate(recorded, sent, mode='valid')
    return np.argmax(np.abs(correlation))
```

---

## Framing: Packet Boundaries

Raw audio is continuous. How does the receiver know when a packet starts?

### Frame Structure

```
[0xAA][0xAA][0xDE][0xAD][Length][Payload...]
└─preamble─┘└──sync───┘
```

- **Preamble (0xAA 0xAA)**: Alternating `10101010` pattern. Distinctive, helps receiver detect "something is starting" and sync its clock.

- **Sync Word (0xDE 0xAD)**: Confirms "this is really a packet, not noise." Unlikely to appear by chance.

- **Length (1 byte)**: How many payload bytes follow (max 255).

- **Payload**: The actual data.

The receiver searches for the known preamble+sync pattern, then reads the length to know when the packet ends.

---

## Error Detection: CRC

### The Problem

Audio transmission is noisy. How do we know if a received packet is valid data or garbage?

### CRC = Cyclic Redundancy Check

CRC treats data as a polynomial and computes the remainder when divided by a fixed "generator polynomial." All arithmetic is done in GF(2) (binary field), where addition = XOR.

### Data as Polynomials

Bits become polynomial coefficients:
```
Data bits:  1 0 1 1
Polynomial: x³ + x + 1  (coefficients for x³, x², x¹, x⁰)
```

### GF(2) Arithmetic

In the binary field GF(2):
- Addition = XOR (1+1=0, no carry)
- Multiplication = AND

This makes computation fast - just bit operations.

### The Algorithm

Given:
- M(x) = message polynomial
- G(x) = generator polynomial (degree n)

1. Append n zeros to message: M(x)·xⁿ
2. Divide by G(x), get remainder R(x)
3. Transmit: T(x) = M(x)·xⁿ + R(x) (message with CRC appended)

### Example

Data: `1101`, Generator: `101` (degree 2)

**Step 1:** Append 2 zeros: `110100`

**Step 2:** Divide using XOR:
```
  110100
  101       ← XOR with generator
  ───
  011100
   101
   ───
   01000
    101
    ───
    0010    ← remainder = 10
```

**Step 3:** Transmit: `1101` + `10` = `110110`

### Why It Works

From division: M(x)·xⁿ = Q(x)·G(x) + R(x)

Rearranging: T(x) = M(x)·xⁿ + R(x) = Q(x)·G(x) + R(x) + R(x)

In GF(2), R(x) + R(x) = 0, so T(x) = Q(x)·G(x)

**T(x) is exactly divisible by G(x).** Receiver divides, expects remainder 0.

### Error Detection

If error E(x) corrupts the message:
- Receiver gets T(x) + E(x)
- Computes (T(x) + E(x)) mod G(x) = E(x) mod G(x)
- If E(x) mod G(x) ≠ 0 → error detected

### Why Certain Errors Are Always Caught

| Error Type | Why Detected |
|------------|--------------|
| Single bit: E(x) = xᵏ | G(x) has multiple terms, so xᵏ mod G(x) ≠ 0 |
| Two bits: xʲ + xᵏ | G(x) chosen to not divide (xᵐ + 1) for small m |
| Odd # of bits | G(x) includes (x+1) as factor |
| Burst ≤ n bits | Degree-n polynomial can't divide shorter burst |

### CRC vs Internet Checksum

| | CRC | Internet Checksum |
|---|-----|-------------------|
| Math | Polynomial division | One's complement sum |
| Detects | Burst errors, specific patterns | Mostly single-bit errors |
| Used in | Ethernet, ZIP, PNG | IP, TCP, UDP headers |

---

## Network Layer Mapping

Our audio modem implements the **Physical** and **Link** layers:

```
┌─────────────────────────────────┐
│  TCP (reliable streams)         │  ← tcp_ip_stack project
├─────────────────────────────────┤
│  IP (routing, addressing)       │  ← tcp_ip_stack project
├─────────────────────────────────┤
│  Framing (packet boundaries)    │  ← audio_modem: preamble/sync/length
├─────────────────────────────────┤
│  FSK Modulation (bits ↔ tones)  │  ← audio_modem: encode/decode
├─────────────────────────────────┤
│  Sound waves through air        │  ← speaker and microphone
└─────────────────────────────────┘
```

This is analogous to how Ethernet creates discrete frames from continuous electrical signals on copper wire.

---

## Project Development

### Phase 1: Tone Generation
- Generate sine waves: `y = A·sin(2πft)`
- Play through speakers using sounddevice
- Test: hear 1000 Hz vs 2000 Hz

### Phase 2: Byte Encoding
- Convert bits to tone sequences
- Encode arbitrary bytes as audio waveforms
- Test: transmit "Hello" as sound

### Phase 3: FFT Decoding
- Implement frequency detection using numpy FFT
- Decode audio back to bits
- Test: encode → decode roundtrip in memory

### Phase 4: Real Audio Loopback
- Play through speaker, record through microphone
- Use cross-correlation to find signal offset
- Test: survive the journey through air

### Phase 5: Framing
- Add preamble, sync word, length header
- Receiver finds packets without knowing content
- Test: decode without knowing original signal

### Phase 6: Integration with TCP/IP Stack (In Progress)
- Use AudioDevice as transport for IP packets
- Parse real IP/TCP headers from audio
- Goal: TCP handshake over sound waves

---

## Usage

```bash
cd audio_modem
source venv/bin/activate
python main.py
```

Tests include:
- Roundtrip encoding/decoding (in memory)
- Real audio loopback with framing
- Fake IP packet transmission

---

## Key Equations

**Sine wave generation:**
```
y(t) = A · sin(2πft)
```

**Samples per bit:**
```
samples = sample_rate × bit_duration = 44100 × 0.01 = 441
```

**Frequency resolution:**
```
resolution = sample_rate / num_samples = 44100 / 441 = 100 Hz
```

**Nyquist limit:**
```
max_frequency = sample_rate / 2 = 22050 Hz
```

---

## Historical Notes

- **1822**: Fourier discovers frequency decomposition while studying heat flow
- **1876**: Bell patents the telephone; Siemens patents the moving-coil transducer
- **1965**: Cooley-Tukey publish the Fast Fourier Transform algorithm
- **1960s-2000s**: Dial-up modems use FSK and more advanced modulation over phone lines
- **Today**: Same principles power WiFi, 5G, Bluetooth - just faster and more sophisticated

---

## Dependencies

- numpy (signal processing, FFT)
- sounddevice (audio I/O)

---

## Future Work

- Two-computer transmission (sender/receiver)
- Full TCP handshake over audio
- Error detection/correction
- Higher baud rates with better modulation (QPSK, QAM)
- Integration as transport layer for tcp_ip_stack
