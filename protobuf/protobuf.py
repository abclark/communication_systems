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


def decode_varint(data: bytes, offset: int = 0) -> tuple[int, int]:
    """
    Decode a varint from bytes.

    Args:
        data: The bytes to decode from
        offset: Starting position in data

    Returns:
        Tuple of (decoded_value, bytes_consumed)
    """
    result = 0
    shift = 0
    position = offset
    while True:
        byte = data[position]
        result |= (byte & 0x7F) << shift
        position += 1
        if (byte & 0x80) == 0:
            break
        shift += 7
    return (result, position - offset)


# =============================================================================
# WIRE TYPES
# =============================================================================

WIRE_TYPE_VARINT = 0  # int32, int64, uint32, uint64, bool, enum
WIRE_TYPE_I64 = 1     # fixed64, sfixed64, double
WIRE_TYPE_LEN = 2     # string, bytes, nested messages, repeated
WIRE_TYPE_I32 = 5     # fixed32, sfixed32, float


# =============================================================================
# TAGS
# =============================================================================

def encode_tag(field_number: int, wire_type: int) -> bytes:
    """Encode a field tag as a varint."""
    tag = (field_number << 3) | wire_type
    return encode_varint(tag)

def decode_tag(data: bytes, offset: int = 0) -> tuple[int, int, int]:
    """
    Decode a tag from bytes.

    Returns: (field_number, wire_type, bytes_consumed)
    """
    tag, length = decode_varint(data, offset)
    wire_type = tag & 0x07
    field_number = tag >> 3
    return (field_number, wire_type, length)


# =============================================================================
# FIELD ENCODING
# =============================================================================

def encode_int_field(field_number: int, value: int) -> bytes:
    """Encode an integer field (wire type 0)."""
    tag = encode_tag(field_number, WIRE_TYPE_VARINT)
    encoded_value = encode_varint(value)
    return tag + encoded_value


def encode_string_field(field_number: int, value: str) -> bytes:
    """Encode a string field (wire type 2)."""
    tag = encode_tag(field_number, WIRE_TYPE_LEN)
    data = value.encode('utf-8')
    length = encode_varint(len(data))
    return tag + length + data

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

    print("Encoding:")
    for value, expected in tests:
        result = encode_varint(value)
        status = "✓" if result == expected else "✗"
        print(f"  {status} encode_varint({value}) = {result.hex() if result else None}, expected {expected.hex()}")

    print("\nDecoding:")
    for expected_value, encoded in tests:
        value, length = decode_varint(encoded)
        status = "✓" if value == expected_value else "✗"
        print(f"  {status} decode_varint({encoded.hex()}) = {value}, expected {expected_value}")

    # Tag tests
    print("\nTags:")
    tag_tests = [
        (1, WIRE_TYPE_VARINT, b'\x08'),   # field 1, varint
        (2, WIRE_TYPE_LEN, b'\x12'),       # field 2, length-delimited
        (3, WIRE_TYPE_VARINT, b'\x18'),   # field 3, varint
        (15, WIRE_TYPE_VARINT, b'\x78'),  # field 15, varint
        (16, WIRE_TYPE_VARINT, b'\x80\x01'),  # field 16, varint (2-byte tag)
    ]
    for field_num, wire_type, expected in tag_tests:
        encoded = encode_tag(field_num, wire_type)
        status = "✓" if encoded == expected else "✗"
        print(f"  {status} encode_tag({field_num}, {wire_type}) = {encoded.hex() if encoded else None}, expected {expected.hex()}")

        # Also test decoding
        decoded_field, decoded_wire, _ = decode_tag(expected)
        status = "✓" if (decoded_field == field_num and decoded_wire == wire_type) else "✗"
        print(f"  {status} decode_tag({expected.hex()}) = field {decoded_field}, wire {decoded_wire}")

    # Field encoding tests
    print("\nInteger fields:")
    field_tests = [
        (1, 150, b'\x08\x96\x01'),     # field 1, value 150
        (2, 300, b'\x10\xac\x02'),     # field 2, value 300
        (1, 1, b'\x08\x01'),           # field 1, value 1
    ]
    for field_num, value, expected in field_tests:
        encoded = encode_int_field(field_num, value)
        status = "✓" if encoded == expected else "✗"
        print(f"  {status} encode_int_field({field_num}, {value}) = {encoded.hex() if encoded else None}, expected {expected.hex()}")

    # String field tests
    print("\nString fields:")
    string_tests = [
        (2, "Alice", b'\x12\x05Alice'),   # field 2, "Alice"
        (1, "hi", b'\x0a\x02hi'),          # field 1, "hi"
        (3, "", b'\x1a\x00'),              # field 3, empty string
    ]
    for field_num, value, expected in string_tests:
        encoded = encode_string_field(field_num, value)
        status = "✓" if encoded == expected else "✗"
        print(f"  {status} encode_string_field({field_num}, '{value}') = {encoded.hex() if encoded else None}, expected {expected.hex()}")
