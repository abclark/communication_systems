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
rtt_samples = []
delivered = 0
delivered_time = None
delivery_rate_samples = []
aes_key = None
conn_id = os.urandom(8)


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
    print(f"[Cache] Saved server public key to {SERVER_CACHE_FILE}")

    shared_secret = crypto.compute_shared_secret(their_public, my_private)
    key = crypto.derive_aes_key(shared_secret)
    print("[Handshake] Shared secret computed, AES key derived")

    return key


def do_0rtt(sock):
    with open(SERVER_CACHE_FILE, 'rb') as f:
        server_public = int.from_bytes(f.read(), 'big')
    print(f"[0-RTT] Loaded cached server public key")

    my_private = crypto.generate_private_key()
    my_public = crypto.compute_public_key(my_private)

    shared_secret = crypto.compute_shared_secret(server_public, my_private)
    key = crypto.derive_aes_key(shared_secret)
    print(f"[0-RTT] Derived key from cached server public")

    return key, my_public


def send_0rtt_data(sock, my_public, stream_id, offset, data):
    frame = frames.encode_stream(stream_id, offset, data.encode('utf-8'))
    encrypted = crypto.encrypt(aes_key, frame)
    payload = (bytes([PACKET_0RTT]) + conn_id + my_public.to_bytes(256, 'big') + encrypted)
    sock.sendto(payload, (DEST_IP, UDP_PORT))
    pending_acks[(stream_id, offset)] = (time.time(), data, delivered, delivered_time)
    print(f"[{conn_id.hex()[:8]}] [0-RTT] [Stream {stream_id}] (offset {offset}) SENT: {data}")


def send_data(sock, stream_id, offset, data):
    frame = frames.encode_stream(stream_id, offset, data.encode('utf-8'))
    encrypted = crypto.encrypt(aes_key, frame)
    payload = bytes([PACKET_DATA]) + conn_id + encrypted
    sock.sendto(payload, (DEST_IP, UDP_PORT))
    pending_acks[(stream_id, offset)] = (time.time(), data, delivered, delivered_time)
    print(f"[{conn_id.hex()[:8]}] [Stream {stream_id}] (offset {offset}) SENT: {data}")


def wait_for_acks(sock, timeout_seconds=2.0):
    global delivered, delivered_time

    while pending_acks:
        try:
            payload, addr = sock.recvfrom(1024)
            if len(payload) >= 10 and payload[0] == PACKET_DATA:
                recv_conn_id = payload[1:9]
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
                            send_time, data, del_at_send, del_time_at_send = pending_acks[key]
                            now = time.time()
                            rtt = now - send_time
                            rtt_samples.append(rtt)

                            delivered += len(data)
                            if del_time_at_send is not None:
                                time_elapsed = now - del_time_at_send
                                if time_elapsed > 0:
                                    rate = (delivered - del_at_send) / time_elapsed
                                    delivery_rate_samples.append(rate)
                            else:
                                rate = len(data) / rtt
                                delivery_rate_samples.append(rate)
                            delivered_time = now

                            del pending_acks[key]
                            print(f"[{recv_conn_id.hex()[:8]}] [Stream {stream_id}] (offset {largest_acked}) ACK received (RTT: {rtt*1000:.1f}ms)")
        except BlockingIOError:
            pass

        now = time.time()
        for key, (send_time, data, _, _) in list(pending_acks.items()):
            if now - send_time > timeout_seconds:
                stream_id, offset = key
                print(f"[Stream {stream_id}] (offset {offset}) TIMEOUT, retransmitting...")
                send_data(sock, stream_id, offset, data)


def main():
    global aes_key

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print("\nSender starting...")
    print("Make sure receiver is running first.")
    print(f"Sending to {DEST_IP}:{UDP_PORT}\n")

    if os.path.exists(SERVER_CACHE_FILE):
        print("=== 0-RTT MODE (cached key found) ===\n")
        aes_key, my_public = do_0rtt(sock)

        sock.setblocking(False)
        send_0rtt_data(sock, my_public, stream_id=1, offset=0, data="hello")
        send_0rtt_data(sock, my_public, stream_id=1, offset=5, data="world")
        wait_for_acks(sock)

        print("\n=== 0-RTT successful! No handshake needed. ===")
        if rtt_samples:
            print(f"\n[RTT Stats] min={min(rtt_samples)*1000:.1f}ms max={max(rtt_samples)*1000:.1f}ms samples={len(rtt_samples)}")
        if delivery_rate_samples:
            print(f"[BW Stats] max={max(delivery_rate_samples)/1000:.1f} KB/s samples={len(delivery_rate_samples)}")
        return
    else:
        print("=== FULL HANDSHAKE (no cache) ===\n")
        aes_key = do_handshake(sock)
        print()

    sock.setblocking(False)
    print("--- Phase 1: Sending from original port ---")
    send_data(sock, stream_id=1, offset=0, data="hello")
    send_data(sock, stream_id=1, offset=5, data="world")
    wait_for_acks(sock)

    print("\n--- Phase 2: Simulating migration (new port) ---")
    sock.close()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    print("[MIGRATION] Closed old socket, opened new one")

    send_data(sock, stream_id=1, offset=10, data="still")
    send_data(sock, stream_id=1, offset=15, data="connected!")
    wait_for_acks(sock)

    print("\n=== Migration successful! Connection survived port change. ===")

    if rtt_samples:
        print(f"\n[RTT Stats] min={min(rtt_samples)*1000:.1f}ms max={max(rtt_samples)*1000:.1f}ms samples={len(rtt_samples)}")
    if delivery_rate_samples:
        print(f"[BW Stats] max={max(delivery_rate_samples)/1000:.1f} KB/s samples={len(delivery_rate_samples)}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nDone.")
