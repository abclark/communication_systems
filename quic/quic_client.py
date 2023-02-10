"""
QUIC Client - class-based wrapper for clean HTTP/3 integration.
"""

import os
import socket

import crypto
import varint
import frames


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
        # TODO: implement
        pass

    def send(self, stream_id: int, data: bytes):
        """Send data on a stream."""
        # TODO: implement
        pass

    def receive(self) -> bytes:
        """Receive data from server."""
        # TODO: implement
        pass

    def close(self):
        """Close the connection."""
        if self.sock:
            self.sock.close()
            self.sock = None
