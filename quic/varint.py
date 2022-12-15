"""
QUIC Variable-Length Integer Encoding (RFC 9000, Section 16)

First 2 bits indicate length:
  00 → 1 byte  (6-bit value,  0 to 63)
  01 → 2 bytes (14-bit value, 0 to 16,383)
  10 → 4 bytes (30-bit value, 0 to 1,073,741,823)
  11 → 8 bytes (62-bit value, 0 to 4,611,686,018,427,387,903)
"""

MAX_1_BYTE = 63
MAX_2_BYTE = 16383
MAX_4_BYTE = 1073741823
MAX_8_BYTE = 4611686018427387903


def encode(value):
    if value < 0:
        raise ValueError("Varint cannot be negative")

    if value <= MAX_1_BYTE:
        return bytes([value])

    elif value <= MAX_2_BYTE:
        return bytes([
            0x40 | (value >> 8),
            value & 0xFF
        ])

    elif value <= MAX_4_BYTE:
        return bytes([
            0x80 | (value >> 24),
            (value >> 16) & 0xFF,
            (value >> 8) & 0xFF,
            value & 0xFF
        ])

    elif value <= MAX_8_BYTE:
        return bytes([
            0xC0 | (value >> 56),
            (value >> 48) & 0xFF,
            (value >> 40) & 0xFF,
            (value >> 32) & 0xFF,
            (value >> 24) & 0xFF,
            (value >> 16) & 0xFF,
            (value >> 8) & 0xFF,
            value & 0xFF
        ])

    else:
        raise ValueError(f"Value {value} too large for varint (max {MAX_8_BYTE})")


def decode(data):
    if len(data) < 1:
        raise ValueError("Not enough data to decode varint")

    first_byte = data[0]
    prefix = first_byte >> 6

    if prefix == 0b00:
        value = first_byte & 0x3F
        return value, 1

    elif prefix == 0b01:
        if len(data) < 2:
            raise ValueError("Not enough data for 2-byte varint")
        value = ((first_byte & 0x3F) << 8) | data[1]
        return value, 2

    elif prefix == 0b10:
        if len(data) < 4:
            raise ValueError("Not enough data for 4-byte varint")
        value = ((first_byte & 0x3F) << 24) | (data[1] << 16) | (data[2] << 8) | data[3]
        return value, 4

    else:
        if len(data) < 8:
            raise ValueError("Not enough data for 8-byte varint")
        value = ((first_byte & 0x3F) << 56) | (data[1] << 48) | (data[2] << 40) | (data[3] << 32) | \
                (data[4] << 24) | (data[5] << 16) | (data[6] << 8) | data[7]
        return value, 8
