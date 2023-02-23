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
