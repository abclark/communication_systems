import sys
sys.path.insert(0, '../tcp_ip_stack')

import sounddevice as sd
import numpy as np
import phy
from packet_headers import IPHeader, ICMPMessage, TCPHeader
import protocols


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


def test_audio_device():
    print("=== AudioDevice Test (Fake IP Packet) ===\n")

    fake_ip_packet = bytes([
        0x45, 0x00, 0x00, 0x1c,  # Version, IHL, TOS, Total Length (28 bytes)
        0x00, 0x01, 0x00, 0x00,  # ID, Flags, Fragment Offset
        0x40, 0x01, 0x00, 0x00,  # TTL=64, Protocol=ICMP, Checksum (placeholder)
        0x0a, 0x00, 0x00, 0x01,  # Source IP: 10.0.0.1
        0x0a, 0x00, 0x00, 0x02,  # Dest IP: 10.0.0.2
        0x08, 0x00, 0x00, 0x00,  # ICMP Echo Request
        0x00, 0x01, 0x00, 0x01,  # ICMP ID and Sequence
    ])

    print(f"1. Fake IP packet ({len(fake_ip_packet)} bytes):")
    print(f"   {fake_ip_packet.hex()}")

    frame = phy.encode_frame(fake_ip_packet)
    frame_duration = len(frame) / phy.SAMPLE_RATE

    padding_samples = int(0.5 * phy.SAMPLE_RATE)
    silence = np.zeros(padding_samples, dtype=np.float32)
    wave_to_play = np.concatenate([silence, frame, silence])

    print(f"\n2. Transmitting via audio ({frame_duration:.2f} sec)...")
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

    print("3. Decoding...")
    received = phy.decode_frame(recording)

    status = "SUCCESS" if received == fake_ip_packet else "FAILED"
    print(f"\n   Sent:     {fake_ip_packet.hex()}")
    print(f"   Received: {received.hex()}")
    print(f"   Status:   {status}")

    if received == fake_ip_packet:
        print("\n   IP packet survived the audio journey!")

        print("\n4. Parsing as IP packet...")
        ip_header = IPHeader.from_bytes(received)
        print(f"   {ip_header}")

        icmp_bytes = received[ip_header.ihl * 4:]
        icmp_msg = ICMPMessage.from_bytes(icmp_bytes)
        print(f"   {icmp_msg}")

    print("\n=== AudioDevice Test Complete ===\n")


def test_tcp_syn():
    print("=== TCP SYN over Audio ===\n")

    src_ip = '10.0.0.1'
    dest_ip = '10.0.0.2'
    src_port = 12345
    dest_port = 80
    seq_num = 1000

    print("1. Building TCP SYN packet...")
    tcp_header = TCPHeader(
        src_port=src_port,
        dest_port=dest_port,
        seq_num=seq_num,
        ack_num=0,
        flags=protocols.TCP_FLAG_SYN,
        window=65535,
        checksum=0,
        urgent_ptr=0,
        payload=b''
    )
    tcp_bytes = tcp_header.to_bytes(src_ip, dest_ip)
    print(f"   TCP header: {len(tcp_bytes)} bytes")

    ip_header = IPHeader(
        version=4,
        ihl=5,
        tos=0,
        total_length=20 + len(tcp_bytes),
        identification=1,
        flags_offset=0,
        ttl=64,
        protocol=protocols.PROTO_TCP,
        checksum=0,
        src_ip=src_ip,
        dest_ip=dest_ip
    )
    ip_bytes = ip_header.to_bytes()
    print(f"   IP header:  {len(ip_bytes)} bytes")

    packet = ip_bytes + tcp_bytes
    print(f"   Total:      {len(packet)} bytes")

    print("2. Transmitting via audio...")
    frame = phy.encode_frame(packet)
    frame_duration = len(frame) / phy.SAMPLE_RATE

    padding_samples = int(0.5 * phy.SAMPLE_RATE)
    silence = np.zeros(padding_samples, dtype=np.float32)
    wave_to_play = np.concatenate([silence, frame, silence])

    print(f"   Frame duration: {frame_duration:.2f} sec")
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

    print("3. Decoding received audio...")
    received = phy.decode_frame(recording)

    status = "SUCCESS" if received == packet else "FAILED"
    print(f"   Sent:     {packet.hex()}")
    print(f"   Received: {received.hex()}")
    print(f"   Status:   {status}")

    if received == packet:
        print("\n4. Parsing received packet...")
        rx_ip = IPHeader.from_bytes(received)
        print(f"   {rx_ip}")

        rx_tcp_bytes = received[rx_ip.ihl * 4:]
        rx_tcp = TCPHeader.from_bytes(rx_tcp_bytes)
        print(f"   {rx_tcp}")

    print("\n=== TCP SYN Test Complete ===\n")


def listen_for_packet(timeout=10):
    print(f"=== Listening for {timeout} seconds ===\n")

    num_samples = int(timeout * phy.SAMPLE_RATE)
    print("Waiting for incoming packet...")
    recording = sd.rec(num_samples, samplerate=phy.SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()
    recording = recording.flatten()

    print("Decoding...")
    received = phy.decode_frame(recording)
    print(f"Received {len(received)} bytes: {received.hex()}")

    print("Parsing...")
    ip_header = IPHeader.from_bytes(received)
    print(f"   {ip_header}")

    if ip_header.protocol == protocols.PROTO_TCP:
        tcp_bytes = received[ip_header.ihl * 4:]
        tcp_header = TCPHeader.from_bytes(tcp_bytes)
        print(f"   {tcp_header}")
    elif ip_header.protocol == protocols.PROTO_ICMP:
        icmp_bytes = received[ip_header.ihl * 4:]
        icmp_msg = ICMPMessage.from_bytes(icmp_bytes)
        print(f"   {icmp_msg}")

    print("\n=== Listener Complete ===\n")


def tcp_server():
    print("=== TCP Server (waiting for SYN) ===\n")

    print("1. Listening for SYN...")
    num_samples = int(30 * phy.SAMPLE_RATE)
    recording = sd.rec(num_samples, samplerate=phy.SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()
    recording = recording.flatten()

    received = phy.decode_frame(recording)
    ip_header = IPHeader.from_bytes(received)
    tcp_header = TCPHeader.from_bytes(received[ip_header.ihl * 4:])
    print(f"   {ip_header}")
    print(f"   {tcp_header}")

    if not (tcp_header.flags & protocols.TCP_FLAG_SYN):
        print("   Not a SYN packet, aborting.")
        return

    print("\n2. Building SYN-ACK response...")
    my_seq = 2000
    their_seq = tcp_header.seq_num

    reply_tcp = TCPHeader(
        src_port=tcp_header.dest_port,
        dest_port=tcp_header.src_port,
        seq_num=my_seq,
        ack_num=their_seq + 1,
        flags=protocols.TCP_FLAG_SYN | protocols.TCP_FLAG_ACK,
        window=65535,
        checksum=0,
        urgent_ptr=0,
        payload=b''
    )
    reply_tcp_bytes = reply_tcp.to_bytes(ip_header.dest_ip, ip_header.src_ip)

    reply_ip = IPHeader(
        version=4,
        ihl=5,
        tos=0,
        total_length=20 + len(reply_tcp_bytes),
        identification=1,
        flags_offset=0,
        ttl=64,
        protocol=protocols.PROTO_TCP,
        checksum=0,
        src_ip=ip_header.dest_ip,
        dest_ip=ip_header.src_ip
    )
    reply_ip_bytes = reply_ip.to_bytes()

    reply_packet = reply_ip_bytes + reply_tcp_bytes
    print(f"   SYN-ACK: seq={my_seq}, ack={their_seq + 1}")

    print("\n3. Sending SYN-ACK...")
    frame = phy.encode_frame(reply_packet)
    padding = np.zeros(int(0.5 * phy.SAMPLE_RATE), dtype=np.float32)
    wave = np.concatenate([padding, frame, padding])
    sd.play(wave, phy.SAMPLE_RATE)
    sd.wait()
    print("   Sent!")

    print("\n=== TCP Server Complete ===\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <command>")
        print("Commands: server, client, syn, listen")
        return

    command = sys.argv[1]

    if command == 'server':
        tcp_server()
    elif command == 'client':
        tcp_client()
    elif command == 'syn':
        test_tcp_syn()
    elif command == 'listen':
        timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        listen_for_packet(timeout)
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
