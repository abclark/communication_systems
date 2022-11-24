import os
import socket
import time
import crypto

DEST_IP = '192.168.100.100'
UDP_PORT = 9000

PACKET_DATA = 0x01
PACKET_ACK = 0x02
PACKET_INIT = 0x03
PACKET_ACCEPT = 0x04

pending_acks = {}
aes_key = None
conn_id = os.urandom(8)  # Random 8-byte Connection ID


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

    their_public = int.from_bytes(response[1:257], 'big')
    print("[Handshake] ACCEPT received (server DH public key)")

    shared_secret = crypto.compute_shared_secret(their_public, my_private)
    key = crypto.derive_aes_key(shared_secret)
    print("[Handshake] Shared secret computed, AES key derived")

    return key


def send_data(sock, stream_id, seq, data):
    plaintext = data.encode('utf-8')
    encrypted = crypto.encrypt(aes_key, plaintext)
    payload = bytes([PACKET_DATA, stream_id]) + seq.to_bytes(2, 'big') + encrypted
    sock.sendto(payload, (DEST_IP, UDP_PORT))
    pending_acks[(stream_id, seq)] = (time.time(), data)
    print(f"[Stream {stream_id}] (seq {seq}) SENT (encrypted): {data}")


def main():
    global aes_key

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print("\nSender starting...")
    print("Make sure receiver is running first.")
    print(f"Sending to {DEST_IP}:{UDP_PORT}\n")

    aes_key = do_handshake(sock)
    print()

    sock.setblocking(False)
    send_data(sock, stream_id=1, seq=1, data="hello")
    send_data(sock, stream_id=1, seq=2, data="world")

    timeout_seconds = 2.0

    while pending_acks:
        try:
            payload, addr = sock.recvfrom(1024)
            if len(payload) >= 4 and payload[0] == PACKET_ACK:
                stream_id = payload[1]
                seq = int.from_bytes(payload[2:4], 'big')

                key = (stream_id, seq)
                if key in pending_acks:
                    del pending_acks[key]
                    print(f"[Stream {stream_id}] (seq {seq}) ACK received")
        except BlockingIOError:
            pass

        now = time.time()
        for key, (send_time, data) in list(pending_acks.items()):
            if now - send_time > timeout_seconds:
                stream_id, seq = key
                print(f"[Stream {stream_id}] (seq {seq}) TIMEOUT, retransmitting...")
                send_data(sock, stream_id, seq, data)

    print("\nAll packets ACKed!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nDone.")
