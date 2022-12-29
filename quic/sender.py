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

pending_acks = {}
aes_key = None
conn_id = os.urandom(8)
rtt_samples = []
packets_sent = 0
rtprop = None
cwnd = 1
last_cwnd_update = 0

RTT_THRESHOLD = 1.25
DRAIN_EXIT = 1.10
CRUISE_DURATION = 5.0

state = 'STARTUP'
state_start_time = 0
last_send_time = 0


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


def update_cwnd():
    global cwnd, last_cwnd_update, rtprop, state, state_start_time

    if len(rtt_samples) < 20:
        return

    now = time.time()
    if now - last_cwnd_update < 0.5:
        return

    recent = rtt_samples[-50:]
    avg_rtt = sum(recent) / len(recent)
    min_rtt = min(recent)
    if rtprop is None or min_rtt < rtprop:
        rtprop = min_rtt

    ratio = avg_rtt / rtprop

    if state == 'STARTUP':
        if ratio < RTT_THRESHOLD:
            cwnd = cwnd + 1 if cwnd < 10 else int(cwnd * 1.25)
        else:
            state = 'DRAIN'
            state_start_time = now

    elif state == 'CRUISE':
        if now - state_start_time > CRUISE_DURATION:
            state = 'PROBE'
            state_start_time = now

    elif state == 'PROBE':
        if ratio < RTT_THRESHOLD:
            cwnd = cwnd + 1 if cwnd < 10 else int(cwnd * 1.25)
        else:
            state = 'DRAIN'
            state_start_time = now

    elif state == 'DRAIN':
        if ratio < DRAIN_EXIT:
            state = 'CRUISE'
            state_start_time = now
        else:
            cwnd = max(1, cwnd - 1)

    print(f"cwnd={cwnd:4} | avg={avg_rtt*1000:.1f}ms | {ratio:.2f}x | {state}")
    last_cwnd_update = now


def print_stats():
    print(f"\n{'='*40}")
    print(f"Packets sent: {packets_sent}")
    print(f"Packets acked: {len(rtt_samples)}")
    print(f"Final cwnd: {cwnd}")
    if rtprop:
        print(f"RTprop: {rtprop*1000:.1f}ms")
    print(f"{'='*40}")


def main():
    global aes_key, last_send_time

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f"\nSending to {DEST_IP}:{UDP_PORT}")
    print(f"States: STARTUP → CRUISE ({CRUISE_DURATION}s) → PROBE → DRAIN → ...")
    print("Press Ctrl+C to stop\n")

    MSG_SIZE = 1000
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
        now = time.time()
        pacing_interval = rtprop / cwnd if rtprop and cwnd > 0 else 0

        if len(pending_acks) < cwnd and now - last_send_time >= pacing_interval:
            send_data(sock, stream_id=1, offset=offset, data=message)
            offset += len(message)
            last_send_time = now

        process_acks(sock)
        update_cwnd()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print_stats()
