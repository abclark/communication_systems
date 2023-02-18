"""
HTTP/3 Client - sends requests over QUIC.
"""

import sys
sys.path.insert(0, '../quic')

from http3 import build_request, parse_response
from quic_client import QUICClient


def request(host, port, method, path):
    client = QUICClient(host, port)
    client.connect()

    req = build_request(method, path)
    client.send(stream_id=0, data=req)

    response = None
    while response is None:
        response = client.receive()

    client.close()

    status, body = parse_response(response)
    return status, body
