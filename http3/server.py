"""
HTTP/3 Server - receives requests over QUIC, sends responses.
"""

import os
import sys
sys.path.insert(0, '../tcp_ip_stack')
sys.path.insert(0, '../quic')

from stack import TunDevice
from packet_headers import IPHeader, UDPHeader
import protocols
import crypto
import frames
from http3 import parse_request, build_response

UDP_PORT = 9000
SERVER_KEY_FILE = 'server_key.bin'

PACKET_DATA = 0x01
PACKET_INIT = 0x03
PACKET_ACCEPT = 0x04

connections = {}


def load_or_generate_server_key():
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

    print("\nHTTP/3 Server listening on port 9000...")
    print("Configure: sudo ifconfig utun<X> 192.168.100.1 192.168.100.2 netmask 255.255.255.0 up")
    input("\nPress Enter after configuring interface...")

    while True:
        packet_bytes = tun.read()
        if not packet_bytes:
            continue

        ip_header = IPHeader.from_bytes(packet_bytes)
        if ip_header.protocol != protocols.PROTO_UDP:
            continue

        udp_bytes = packet_bytes[ip_header.ihl * 4:]
        udp_header = UDPHeader.from_bytes(udp_bytes)

        if udp_header.dest_port != UDP_PORT:
            continue

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
                'client_ip': ip_header.src_ip,
                'client_port': udp_header.src_port
            }
            print(f"[{conn_id.hex()[:8]}] Connection established")

            accept_payload = bytes([PACKET_ACCEPT]) + conn_id + server_public.to_bytes(256, 'big')
            send_udp(tun, ip_header.dest_ip, UDP_PORT, ip_header.src_ip, udp_header.src_port, accept_payload)
            print(f"[{conn_id.hex()[:8]}] ACCEPT sent\n")

        elif packet_type == PACKET_DATA:
            conn_id = payload[1:9]
            if conn_id not in connections:
                print(f"[{conn_id.hex()[:8]}] Unknown connection, dropping")
                continue

            conn = connections[conn_id]
            encrypted = payload[9:]
            decrypted = crypto.decrypt(conn['aes_key'], encrypted)

            frame_type, frame_data, _ = frames.decode_frame(decrypted)
            if frame_type != frames.FRAME_STREAM:
                continue

            stream_id, offset, request_bytes = frame_data
            method, path = parse_request(request_bytes)
            print(f"[{conn_id.hex()[:8]}] Request: {method} {path}")

            if path == "/hello":
                response_bytes = build_response(200, b"Hello World")
            else:
                response_bytes = build_response(404, b"Not Found")

            response_frame = frames.encode_stream(stream_id, 0, response_bytes)
            response_encrypted = crypto.encrypt(conn['aes_key'], response_frame)
            response_packet = bytes([PACKET_DATA]) + conn_id + response_encrypted

            send_udp(tun, ip_header.dest_ip, UDP_PORT, ip_header.src_ip, udp_header.src_port, response_packet)
            print(f"[{conn_id.hex()[:8]}] Response: 200 OK\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down.")
