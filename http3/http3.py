"""
HTTP/3 - Built from scratch on top of QUIC.
"""

import sys
sys.path.append('..')
from protobuf.protobuf import encode_varint

# =============================================================================
# FRAME TYPES
# =============================================================================

FRAME_DATA = 0x00      # Request/response body
FRAME_HEADERS = 0x01   # HTTP headers (method, path, status, etc.)


# =============================================================================
# FRAME ENCODING
# =============================================================================

def encode_frame(frame_type: int, payload: bytes) -> bytes:
    """
    Encode an HTTP/3 frame.

    Structure: [Type (varint)] [Length (varint)] [Payload]
    """
    type_bytes = encode_varint(frame_type)
    length_bytes = encode_varint(len(payload))
    return type_bytes + length_bytes + payload


# =============================================================================
# TESTS
# =============================================================================

if __name__ == "__main__":
    print("HTTP/3 Frame Tests")
    print("=" * 40)

    # Test: DATA frame with "Hello"
    frame = encode_frame(FRAME_DATA, b"Hello")
    print(f"\nDATA frame with 'Hello':")
    print(f"  Raw bytes: {frame}")
    print(f"  Hex:       {frame.hex()}")
    print(f"  Breakdown:")
    print(f"    Type:    {frame[0]:02x} (DATA)")
    print(f"    Length:  {frame[1]:02x} (5 bytes)")
    print(f"    Payload: {frame[2:]}")
