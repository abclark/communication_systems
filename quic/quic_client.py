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
        private_key = crypto.generate_private_key()
        public_key = crypto.compute_public_key(private_key)

        init_packet = bytes([PACKET_INIT]) + self.conn_id + public_key.to_bytes(256, 'big')
        self.sock.sendto(init_packet, (self.host, self.port))

        response, _ = self.sock.recvfrom(4096)
        server_public = int.from_bytes(response[9:265], 'big')

        shared_secret = crypto.compute_shared_secret(server_public, private_key)
        return crypto.derive_aes_key(shared_secret)

    def send(self, stream_id: int, data: bytes):
        """Send data on a stream."""
        frame = frames.encode_stream(stream_id, 0, data)
        encrypted = crypto.encrypt(self.aes_key, frame)
        packet = bytes([PACKET_DATA]) + self.conn_id + encrypted
        self.sock.sendto(packet, (self.host, self.port))

    def receive(self) -> bytes:
        """Receive data from server."""
        try:
            packet, _ = self.sock.recvfrom(4096)
        except BlockingIOError:
            return None

        encrypted = packet[9:]
        decrypted = crypto.decrypt(self.aes_key, encrypted)
        frame_type, frame_data, _ = frames.decode_frame(decrypted)
        if frame_type == frames.FRAME_STREAM and frame_data:
            stream_id, offset, data = frame_data
            return data
        return None

    def close(self):
        """Close the connection."""
        if self.sock:
            self.sock.close()
            self.sock = None
