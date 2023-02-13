"""
QUIC Client - class-based wrapper for clean HTTP/3 integration.
"""

import os
import socket

import crypto
import varint
import frames

# Packet types
PACKET_DATA = 0x01
PACKET_INIT = 0x03
PACKET_ACCEPT = 0x04


class QUICClient:
    """A QUIC client connection."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sock = None
        self.aes_key = None
        self.conn_id = None

    def connect(self):
        """Open socket and perform QUIC handshake."""
        # Create UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.conn_id = os.urandom(8)

        # Do handshake (get encryption key)
        self.aes_key = self._do_handshake()

        # Set non-blocking for receive
        self.sock.setblocking(False)

    def _do_handshake(self):
        """Perform QUIC handshake, return AES key."""
        private_key, public_key = crypto.generate_keypair()

        init_packet = bytes([PACKET_INIT]) + self.conn_id + public_key
        self.sock.sendto(init_packet, (self.host, self.port))

        response, _ = self.sock.recvfrom(1024)
        server_public = response[1:33]

        return crypto.compute_shared_secret(private_key, server_public)

    def send(self, stream_id: int, data: bytes):
        """Send data on a stream."""
        frame = frames.build_stream_frame(stream_id, 0, data)
        encrypted = crypto.encrypt(self.aes_key, frame)
        packet = bytes([PACKET_DATA]) + self.conn_id + encrypted
        self.sock.sendto(packet, (self.host, self.port))

    def receive(self) -> bytes:
        """Receive data from server."""
        # TODO: implement
        pass

    def close(self):
        """Close the connection."""
        if self.sock:
            self.sock.close()
            self.sock = None
