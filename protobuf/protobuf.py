"""
Protocol Buffers - Built from scratch.
"""


def encode_varint(n: int) -> bytes:
    """
    Encode an integer as a protobuf varint.

    Each byte uses 7 bits for data, 1 bit (MSB) as continuation flag.
    Least significant bits come first.
    """
    result = []
    while True:
        byte = n & 0x7F
        n >>= 7
        if n > 0:
            byte |= 0x80
        result.append(byte)
        if n == 0:
            break
    return bytes(result)

# Quick test
if __name__ == "__main__":
    # Test cases: (input, expected_output)
    tests = [
        (1, b'\x01'),
        (127, b'\x7f'),
        (128, b'\x80\x01'),
        (150, b'\x96\x01'),
        (300, b'\xac\x02'),
    ]

    for value, expected in tests:
        result = encode_varint(value)
        status = "✓" if result == expected else "✗"
        print(f"{status} encode_varint({value}) = {result.hex() if result else None}, expected {expected.hex()}")
