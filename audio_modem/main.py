"""
main.py - Audio Modem Test Script

Run this to hear your bits become sound!
"""

import sounddevice as sd
import phy


def play(samples, sample_rate=phy.SAMPLE_RATE):
    """Play audio samples through the speaker."""
    sd.play(samples, sample_rate)
    sd.wait()  # Block until playback is finished


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
    test_roundtrip()

    # Then play some audio
    test_audio()


if __name__ == "__main__":
    main()
