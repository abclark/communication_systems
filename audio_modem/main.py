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


def main():
    print("=== Audio Modem - Phase 1: Tone Generation ===\n")

    # Test 1: Play our two frequencies
    print("1. Playing FREQ_0 (1000 Hz) - this represents '0'")
    wave_0 = phy.generate_tone(phy.FREQ_0, duration=0.5)
    play(wave_0)

    print("2. Playing FREQ_1 (2000 Hz) - this represents '1'")
    wave_1 = phy.generate_tone(phy.FREQ_1, duration=0.5)
    play(wave_1)

    # Test 2: Encode a single byte with alternating bits
    print("\n3. Playing byte 0xAA (binary: 10101010)")
    print("   You should hear alternating high-low tones")
    wave_aa = phy.encode_byte(0xAA)
    play(wave_aa)

    # Test 3: Encode a string
    print("\n4. Playing 'Hi' as audio")
    print("   H = 0x48 = 01001000")
    print("   i = 0x69 = 01101001")
    wave_hi = phy.encode_bytes(b"Hi")
    play(wave_hi)

    print("\n=== Done! ===")


if __name__ == "__main__":
    main()
