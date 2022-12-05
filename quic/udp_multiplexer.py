import os
import sys
sys.path.insert(0, '../tcp_ip_stack')

from stack import TunDevice
from packet_headers import IPHeader, UDPHeader
import protocols
import crypto

UDP_PORT = 9000
SERVER_KEY_FILE = 'server_key.bin'


def load_or_generate_server_key():
    """Load server's long-term DH private key, or generate if first run."""
    if os.path.exists(SERVER_KEY_FILE):
        with open(SERVER_KEY_FILE, 'rb') as f:
            private = int.from_bytes(f.read(), 'big')
            print(f"[Server] Loaded existing keypair from {SERVER_KEY_FILE}")
            return private
    else:
        private = crypto.generate_private_key()
        with open(SERVER_KEY_FILE, 'wb') as f:
            f.write(private.to_bytes(32, 'big'))
        print(f"[Server] Generated new keypair, saved to {SERVER_KEY_FILE}")
        return private

PACKET_DATA = 0x01
PACKET_ACK = 0x02
PACKET_INIT = 0x03
PACKET_ACCEPT = 0x04

stream_next_deliver = {1: 1, 2: 1, 3: 1}
stream_pending = {1: [], 2: [], 3: []}
delayed_messages = []
connections = {}


def send_udp(tun, src_ip, src_port, dest_ip, dest_port, payload):
    udp = UDPHeader(
        src_port=src_port,
        dest_port=dest_port,
        length=8 + len(payload),
        checksum=0,
        payload=payload
    )
    udp_bytes = udp.to_bytes(src_ip, dest_ip)

    ip = IPHeader(
        version=4,
        ihl=5,
        tos=0,
        total_length=20 + len(udp_bytes),
        identification=0,
        flags_offset=0,
        ttl=64,
        protocol=protocols.PROTO_UDP,
        checksum=0,
        src_ip=src_ip,
        dest_ip=dest_ip
    )
    ip_bytes = ip.to_bytes()
    tun.write(ip_bytes + udp_bytes)


def main():
    server_private = load_or_generate_server_key()
    server_public = crypto.compute_public_key(server_private)

    tun = TunDevice()

    print("\nListening for UDP on port 9000...")
    print("Configure: sudo ifconfig utun<X> 192.168.100.1 192.168.100.2 netmask 255.255.255.0 up")
    print("Packet format: [type 1B][stream 1B][seq 2B][data...]")
    print("  DATA=0x01, ACK=0x02")
    input("\nPress Enter after configuring interface...")

    while True:
        packet_bytes = tun.read()
        if packet_bytes:
            ip_header = IPHeader.from_bytes(packet_bytes)
            if ip_header.protocol == protocols.PROTO_UDP:
                udp_bytes = packet_bytes[ip_header.ihl * 4:]
                udp_header = UDPHeader.from_bytes(udp_bytes)

                if udp_header.dest_port == UDP_PORT:
                    payload = udp_header.payload
                    if len(payload) < 1:
                        continue

                    packet_type = payload[0]

                    if packet_type == PACKET_INIT:
                        conn_id = payload[1:9]
                        their_public = int.from_bytes(payload[9:265], 'big')
                        print(f"[{conn_id.hex()[:8]}] INIT received")

                        shared_secret = crypto.compute_shared_secret(their_public, server_private)
                        aes_key = crypto.derive_aes_key(shared_secret)

                        connections[conn_id] = {
                            'aes_key': aes_key,
                            'last_addr': (ip_header.src_ip, udp_header.src_port)
                        }
                        print(f"[{conn_id.hex()[:8]}] Connection stored (key derived)")

                        accept_payload = bytes([PACKET_ACCEPT]) + conn_id + server_public.to_bytes(256, 'big')
                        send_udp(tun, ip_header.dest_ip, UDP_PORT, ip_header.src_ip, udp_header.src_port, accept_payload)
                        print(f"[{conn_id.hex()[:8]}] ACCEPT sent\n")

                    elif packet_type == PACKET_DATA:
                        if len(payload) < 12:
                            continue
                        conn_id = payload[1:9]
                        stream_id = payload[9]
                        seq = int.from_bytes(payload[10:12], 'big')

                        if conn_id not in connections:
                            print(f"[{conn_id.hex()[:8]}] Unknown connection, dropping")
                            continue

                        conn = connections[conn_id]
                        conn['last_addr'] = (ip_header.src_ip, udp_header.src_port)

                        if stream_id not in stream_next_deliver:
                            continue

                        encrypted = payload[12:]
                        decrypted = crypto.decrypt(conn['aes_key'], encrypted)
                        data = decrypted.decode('utf-8').strip()
                        print(f"[{conn_id.hex()[:8]}] [Stream {stream_id}] (seq {seq}) DATA: {data}")

                        ack_payload = bytes([PACKET_ACK]) + conn_id + bytes([stream_id]) + seq.to_bytes(2, 'big')
                        send_udp(tun, ip_header.dest_ip, UDP_PORT, ip_header.src_ip, udp_header.src_port, ack_payload)
                        print(f"[{conn_id.hex()[:8]}] [Stream {stream_id}] (seq {seq}) ACK sent")

                        stream_pending[stream_id].append((seq, data))

                        stream_pending[stream_id].sort(key=lambda x: x[0])
                        while stream_pending[stream_id] and stream_pending[stream_id][0][0] == stream_next_deliver[stream_id]:
                            msg = stream_pending[stream_id].pop(0)
                            print(f"[Stream {stream_id}] (seq {msg[0]}) DELIVERED: {msg[1]}")
                            stream_next_deliver[stream_id] += 1

                    elif packet_type == PACKET_ACK:
                        stream_id = payload[1]
                        seq = int.from_bytes(payload[2:4], 'big')
                        print(f"[Stream {stream_id}] (seq {seq}) ACK received")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nDone.")
