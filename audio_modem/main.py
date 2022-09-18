import sounddevice as sd
import numpy as np
import phy


def play(samples, sample_rate=phy.SAMPLE_RATE):
    sd.play(samples, sample_rate)
    sd.wait()


def record(duration, sample_rate=phy.SAMPLE_RATE):
    num_samples = int(sample_rate * duration)
    print(f"   Recording {duration} seconds...")
    recording = sd.rec(num_samples, samplerate=sample_rate, channels=1, dtype='float32')
    sd.wait()
    return recording.flatten()


def test_roundtrip():
    print("=== Testing Encode → Decode Roundtrip ===\n")

    print("1. Single bit test:")
    for bit in [0, 1]:
        wave = phy.encode_bit(bit)
        decoded = phy.decode_bit(wave)
        status = "✓" if decoded == bit else "✗"
        print(f"   {bit} → encode → decode → {decoded}  {status}")

    print("\n2. Single byte test:")
    for byte_val in [0x00, 0xFF, 0xAA, 0x55, 0x48]:
        wave = phy.encode_byte(byte_val)
        decoded = phy.decode_byte(wave)
        status = "✓" if decoded == byte_val else "✗"
        print(f"   0x{byte_val:02X} → encode → decode → 0x{decoded:02X}  {status}")

    print("\n3. String test:")
    test_string = b"Hi"
    wave = phy.encode_bytes(test_string)
    decoded = phy.decode_bytes(wave, len(test_string))
    status = "✓" if decoded == test_string else "✗"
    print(f"   {test_string} → encode → decode → {decoded}  {status}")

    print("\n4. Merry Christmas test:")
    test_string = b"Merry Christmas"
    wave = phy.encode_bytes(test_string)
    decoded = phy.decode_bytes(wave, len(test_string))
    status = "✓" if decoded == test_string else "✗"
    print(f"   {test_string}")
    print(f"   → {decoded}  {status}")

    print("\n=== Roundtrip Test Complete ===\n")


def test_loopback():
    print("=== Real Audio Loopback Test (with Framing) ===\n")
    print("This will play audio and record it through your microphone.")
    print("Make sure your speaker volume is up and mic is enabled.\n")

    test_message = b"Yippee ki yay"

    frame = phy.encode_frame(test_message)
    frame_duration = len(frame) / phy.SAMPLE_RATE

    padding_samples = int(0.5 * phy.SAMPLE_RATE)
    silence = np.zeros(padding_samples, dtype=np.float32)
    wave_to_play = np.concatenate([silence, frame, silence])

    print(f"1. Sending: {test_message}")
    print(f"   Frame duration: {frame_duration:.2f} seconds")

    print("2. Playing and recording...")
    recording = sd.playrec(
        wave_to_play,
        samplerate=phy.SAMPLE_RATE,
        channels=1,
        dtype='float32',
        input_mapping=[1],
        output_mapping=[1]
    )
    sd.wait()
    recording = recording.flatten()

    print("3. Decoding frame...")
    decoded = phy.decode_frame(recording)

    status = "SUCCESS" if decoded == test_message else "FAILED"
    print(f"\n   Sent:     {test_message}")
    print(f"   Received: {decoded}")
    print(f"   Status:   {status}")

    if decoded != test_message:
        print("\n   Note: Real audio loopback can fail due to speaker/mic")
        print("   quality, room echo, or noise. Try increasing volume.")

    print("\n=== Loopback Test Complete ===\n")


def test_audio():
    print("=== Audio Playback Test ===\n")

    print("1. Playing FREQ_0 (1000 Hz) - represents '0'")
    play(phy.generate_tone(phy.FREQ_0, duration=0.3))

    print("2. Playing FREQ_1 (2000 Hz) - represents '1'")
    play(phy.generate_tone(phy.FREQ_1, duration=0.3))

    print("\n3. Playing 'Hi' as audio")
    wave = phy.encode_bytes(b"Hi")
    play(wave)

    print("\n4. Playing 'Merry Christmas' as audio (1.2 seconds)")
    wave = phy.encode_bytes(b"Merry Christmas")
    play(wave)

    print("\n=== Audio Test Complete ===")


def main():
    # test_roundtrip()
    test_loopback()
    # test_audio()


if __name__ == "__main__":
    main()
