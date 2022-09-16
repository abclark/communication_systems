"""
main.py - Audio Modem Test Script

Run this to hear your bits become sound!
"""

import sounddevice as sd
import numpy as np
import phy


def play(samples, sample_rate=phy.SAMPLE_RATE):
    """Play audio samples through the speaker."""
    sd.play(samples, sample_rate)
    sd.wait()  # Block until playback is finished


def record(duration, sample_rate=phy.SAMPLE_RATE):
    """Record audio from the microphone."""
    num_samples = int(sample_rate * duration)
    print(f"   Recording {duration} seconds...")
    recording = sd.rec(num_samples, samplerate=sample_rate, channels=1, dtype='float32')
    sd.wait()  # Block until recording is finished
    return recording.flatten()  # Return as 1D array


def test_roundtrip():
    """Test encode → decode without audio (verify the math)."""
    print("=== Testing Encode → Decode Roundtrip ===\n")

    # Test 1: Single bit
    print("1. Single bit test:")
    for bit in [0, 1]:
        wave = phy.encode_bit(bit)
        decoded = phy.decode_bit(wave)
        status = "✓" if decoded == bit else "✗"
        print(f"   {bit} → encode → decode → {decoded}  {status}")

    # Test 2: Single byte
    print("\n2. Single byte test:")
    for byte_val in [0x00, 0xFF, 0xAA, 0x55, 0x48]:
        wave = phy.encode_byte(byte_val)
        decoded = phy.decode_byte(wave)
        status = "✓" if decoded == byte_val else "✗"
        print(f"   0x{byte_val:02X} → encode → decode → 0x{decoded:02X}  {status}")

    # Test 3: String
    print("\n3. String test:")
    test_string = b"Hi"
    wave = phy.encode_bytes(test_string)
    decoded = phy.decode_bytes(wave, len(test_string))
    status = "✓" if decoded == test_string else "✗"
    print(f"   {test_string} → encode → decode → {decoded}  {status}")

    # Test 4: Merry Christmas
    print("\n4. Merry Christmas test:")
    test_string = b"Merry Christmas"
    wave = phy.encode_bytes(test_string)
    decoded = phy.decode_bytes(wave, len(test_string))
    status = "✓" if decoded == test_string else "✗"
    print(f"   {test_string}")
    print(f"   → {decoded}  {status}")

    print("\n=== Roundtrip Test Complete ===\n")


def test_loopback():
    """Test real audio: play through speaker, record through mic, decode."""
    print("=== Real Audio Loopback Test ===\n")
    print("This will play audio and record it through your microphone.")
    print("Make sure your speaker volume is up and mic is enabled.\n")

    test_message = b"Hi"

    # Encode the message
    wave = phy.encode_bytes(test_message)
    duration = len(wave) / phy.SAMPLE_RATE

    print(f"1. Sending: {test_message}")
    print(f"   Duration: {duration:.2f} seconds")

    # Play and record simultaneously
    print("2. Playing and recording...")
    recording = sd.playrec(
        wave,
        samplerate=phy.SAMPLE_RATE,
        channels=1,
        dtype='float32',
        input_mapping=[1],
        output_mapping=[1]
    )
    sd.wait()
    recording = recording.flatten()

    # Decode (assumes recording is aligned - we'll add framing later)
    print("3. Decoding...")
    decoded = phy.decode_bytes(recording, len(test_message))

    status = "SUCCESS" if decoded == test_message else "FAILED"
    print(f"\n   Sent:     {test_message}")
    print(f"   Received: {decoded}")
    print(f"   Status:   {status}")

    if decoded != test_message:
        print("\n   Note: Real audio loopback is hard! The signal may be")
        print("   distorted by speaker/mic quality, room echo, or timing.")
        print("   We'll add framing (preamble/sync) to make this robust.")

    print("\n=== Loopback Test Complete ===\n")


def test_audio():
    """Play encoded audio through speakers."""
    print("=== Audio Playback Test ===\n")

    # Play the two tones
    print("1. Playing FREQ_0 (1000 Hz) - represents '0'")
    play(phy.generate_tone(phy.FREQ_0, duration=0.3))

    print("2. Playing FREQ_1 (2000 Hz) - represents '1'")
    play(phy.generate_tone(phy.FREQ_1, duration=0.3))

    # Play a message
    print("\n3. Playing 'Hi' as audio")
    wave = phy.encode_bytes(b"Hi")
    play(wave)

    # Play Merry Christmas
    print("\n4. Playing 'Merry Christmas' as audio (1.2 seconds)")
    wave = phy.encode_bytes(b"Merry Christmas")
    play(wave)

    print("\n=== Audio Test Complete ===")


def main():
    # First verify the math works
    # test_roundtrip()

    # Test real audio loopback (speaker → mic → decode)
    test_loopback()

    # Then play some audio
    # test_audio()


if __name__ == "__main__":
    main()
