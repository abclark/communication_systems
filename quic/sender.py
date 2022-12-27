import os
import socket
import time
import crypto
import varint
import frames

DEST_IP = '192.168.100.100'
UDP_PORT = 9000
SERVER_CACHE_FILE = 'server_pubkey.bin'

PACKET_DATA = 0x01
PACKET_ACK = 0x02
PACKET_INIT = 0x03
PACKET_ACCEPT = 0x04
PACKET_0RTT = 0x05

# Connection state
pending_acks = {}
aes_key = None
conn_id = os.urandom(8)

# Measurement state
rtt_samples = []
packets_sent = 0

# Congestion window
cwnd = 10               # max packets in flight, start small
last_increase_time = 0


def do_handshake(sock):
    my_private = crypto.generate_private_key()
    my_public = crypto.compute_public_key(my_private)

    init_packet = bytes([PACKET_INIT]) + conn_id + my_public.to_bytes(256, 'big')
    sock.sendto(init_packet, (DEST_IP, UDP_PORT))
    print(f"[Handshake] INIT sent (conn_id={conn_id.hex()[:8]}...)")

    sock.setblocking(True)
    response, addr = sock.recvfrom(1024)
    sock.setblocking(False)

    if response[0] != PACKET_ACCEPT:
        raise Exception("Expected ACCEPT packet")

    recv_conn_id = response[1:9]
    their_public = int.from_bytes(response[9:265], 'big')
    print(f"[{recv_conn_id.hex()[:8]}] ACCEPT received")

    with open(SERVER_CACHE_FILE, 'wb') as f:
        f.write(their_public.to_bytes(256, 'big'))

    shared_secret = crypto.compute_shared_secret(their_public, my_private)
    key = crypto.derive_aes_key(shared_secret)
    print("[Handshake] Complete\n")

    return key


def do_0rtt(sock):
    with open(SERVER_CACHE_FILE, 'rb') as f:
        server_public = int.from_bytes(f.read(), 'big')

    my_private = crypto.generate_private_key()
    my_public = crypto.compute_public_key(my_private)

    shared_secret = crypto.compute_shared_secret(server_public, my_private)
    key = crypto.derive_aes_key(shared_secret)
    print("[0-RTT] Using cached key\n")

    return key, my_public


def send_0rtt_data(sock, my_public, stream_id, offset, data):
    global packets_sent
    frame = frames.encode_stream(stream_id, offset, data.encode('utf-8'))
    encrypted = crypto.encrypt(aes_key, frame)
    payload = (bytes([PACKET_0RTT]) + conn_id + my_public.to_bytes(256, 'big') + encrypted)
    sock.sendto(payload, (DEST_IP, UDP_PORT))
    pending_acks[(stream_id, offset)] = (time.time(), data)
    packets_sent += 1


def send_data(sock, stream_id, offset, data):
    global packets_sent
    frame = frames.encode_stream(stream_id, offset, data.encode('utf-8'))
    encrypted = crypto.encrypt(aes_key, frame)
    payload = bytes([PACKET_DATA]) + conn_id + encrypted
    sock.sendto(payload, (DEST_IP, UDP_PORT))
    pending_acks[(stream_id, offset)] = (time.time(), data)
    packets_sent += 1


def process_acks(sock):
    try:
        while True:
            payload, addr = sock.recvfrom(1024)
            if len(payload) >= 10 and payload[0] == PACKET_DATA:
                encrypted = payload[9:]
                decrypted = crypto.decrypt(aes_key, encrypted)

                pos = 0
                while pos < len(decrypted):
                    frame_type, frame_data, consumed = frames.decode_frame(decrypted[pos:])
                    if frame_type is None:
                        break
                    pos += consumed

                    if frame_type == frames.FRAME_ACK:
                        stream_id, largest_acked = frame_data
                        key = (stream_id, largest_acked)
                        if key in pending_acks:
                            send_time, data = pending_acks[key]
                            rtt = time.time() - send_time
                            rtt_samples.append(rtt)
                            del pending_acks[key]
    except BlockingIOError:
        pass


def print_status():
    global cwnd, last_increase_time

    if len(rtt_samples) < 20:
        return

    now = time.time()
    if now - last_increase_time < 0.5:
        return

    # Get recent RTT stats (last 50 samples)
    recent = rtt_samples[-50:]
    min_rtt = min(recent)
    avg_rtt = sum(recent) / len(recent)
    max_rtt = max(recent)

    # Baseline: min of last 100 samples (rolling window)
    baseline_window = rtt_samples[-100:] if len(rtt_samples) > 100 else rtt_samples[10:]
    baseline = min(baseline_window)
    ratio = avg_rtt / baseline if baseline > 0 else 1.0

    print(f"cwnd={cwnd:4} | RTT: min={min_rtt*1000:.2f} avg={avg_rtt*1000:.2f} max={max_rtt*1000:.2f} ms | {ratio:.1f}x baseline | samples={len(rtt_samples)}")

    # Increase cwnd
    cwnd = int(cwnd * 1.25) if cwnd < 10000 else cwnd
    last_increase_time = now


def print_stats():
    print(f"\n{'='*50}")
    print(f"  FINAL STATS")
    print(f"{'='*50}")
    print(f"Packets sent: {packets_sent}")
    print(f"Packets acked: {len(rtt_samples)}")
    print(f"Pending: {len(pending_acks)}")

    if len(rtt_samples) > 20:
        samples = rtt_samples[10:]  # skip warmup
        rtprop = min(samples)
        rtt_max = max(samples)
        print(f"\nRTprop (min RTT): {rtprop*1000:.2f}ms")
        print(f"RTT max:          {rtt_max*1000:.2f}ms")
        print(f"RTT max / RTprop: {rtt_max/rtprop:.1f}x")
    print(f"{'='*50}")


def main():
    global aes_key

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print("\n=== CWND Test ===")
    print(f"Sending to {DEST_IP}:{UDP_PORT}")
    print("Increasing cwnd by 25% every 0.5s")
    print("Watch RTT to see when queuing starts")
    print("Press Ctrl+C to stop\n")

    # Larger messages to create congestion
    MSG_SIZE = 1000  # 1KB chunks
    message = "X" * MSG_SIZE
    offset = 0

    if os.path.exists(SERVER_CACHE_FILE):
        aes_key, my_public = do_0rtt(sock)
        sock.setblocking(False)
        send_0rtt_data(sock, my_public, stream_id=1, offset=0, data="init")
        offset = 4
    else:
        aes_key = do_handshake(sock)
        sock.setblocking(False)

    while True:
        # Only send if under cwnd limit
        while len(pending_acks) < cwnd:
            send_data(sock, stream_id=1, offset=offset, data=message)
            offset += len(message)

        process_acks(sock)
        print_status()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print_stats()
