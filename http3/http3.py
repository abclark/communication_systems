"""
HTTP/3 - Built from scratch on top of QUIC.
"""

import sys
sys.path.append('..')
from protobuf.protobuf import encode_varint, decode_varint

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


def decode_frame(data: bytes, offset: int = 0) -> tuple[int, bytes, int]:
    """
    Decode an HTTP/3 frame.

    Returns: (frame_type, payload, bytes_consumed)
    """
    # Read type
    frame_type, type_size = decode_varint(data, offset)

    # Read length
    length, length_size = decode_varint(data, offset + type_size)

    # Read payload
    payload_start = offset + type_size + length_size
    payload = data[payload_start : payload_start + length]

    total_consumed = type_size + length_size + length
    return (frame_type, payload, total_consumed)


# =============================================================================
# HEADER ENCODING
# =============================================================================

def encode_headers(headers: dict) -> bytes:
    """
    Encode headers as: [name_len][name][value_len][value]...
    """
    result = b''
    for name, value in headers.items():
        name_bytes = name.encode('utf-8')
        value_bytes = value.encode('utf-8')
        result += encode_varint(len(name_bytes)) + name_bytes
        result += encode_varint(len(value_bytes)) + value_bytes
    return result


def decode_headers(data: bytes) -> dict:
    """
    Decode headers from: [name_len][name][value_len][value]...
    """
    headers = {}
    offset = 0
    while offset < len(data):
        # Read name
        name_len, consumed = decode_varint(data, offset)
        offset += consumed
        name = data[offset : offset + name_len].decode('utf-8')
        offset += name_len

        # Read value
        value_len, consumed = decode_varint(data, offset)
        offset += consumed
        value = data[offset : offset + value_len].decode('utf-8')
        offset += value_len

        headers[name] = value
    return headers


# =============================================================================
# TESTS
# =============================================================================

if __name__ == "__main__":
    print("HTTP/3 Frame Tests")
    print("=" * 40)

    # Test 1: Encode DATA frame
    frame = encode_frame(FRAME_DATA, b"Hello")
    print(f"\n1. Encode DATA frame with 'Hello':")
    print(f"   Hex: {frame.hex()}")

    # Test 2: Decode it back
    frame_type, payload, consumed = decode_frame(frame)
    print(f"\n2. Decode it back:")
    print(f"   Type:     {frame_type} ({'DATA' if frame_type == 0 else 'HEADERS'})")
    print(f"   Payload:  {payload}")
    print(f"   Consumed: {consumed} bytes")

    # Test 3: Round-trip check
    success = frame_type == FRAME_DATA and payload == b"Hello"
    print(f"\n3. Round-trip: {'✓ Pass' if success else '✗ Fail'}")

    # Test 4: Encode headers
    headers = {":method": "GET", ":path": "/hello"}
    encoded = encode_headers(headers)
    print(f"\n4. Encode headers:")
    print(f"   Input:  {headers}")
    print(f"   Hex:    {encoded.hex()}")

    # Test 5: Decode headers
    decoded = decode_headers(encoded)
    print(f"\n5. Decode headers:")
    print(f"   Output: {decoded}")
    success = decoded == headers
    print(f"   Round-trip: {'✓ Pass' if success else '✗ Fail'}")
