import varint

FRAME_STREAM = 0x08
FRAME_ACK = 0x02


def encode_stream(stream_id, offset, data):
    return (
        varint.encode(FRAME_STREAM) +
        varint.encode(stream_id) +
        varint.encode(offset) +
        varint.encode(len(data)) +
        data
    )


def decode_stream(data):
    pos = 0

    stream_id, n = varint.decode(data[pos:])
    pos += n

    offset, n = varint.decode(data[pos:])
    pos += n

    length, n = varint.decode(data[pos:])
    pos += n

    payload = data[pos:pos + length]
    pos += length

    return stream_id, offset, payload, pos


def encode_ack(stream_id, largest_acked):
    return (
        varint.encode(FRAME_ACK) +
        varint.encode(stream_id) +
        varint.encode(largest_acked)
    )


def decode_ack(data):
    pos = 0

    stream_id, n = varint.decode(data[pos:])
    pos += n

    largest_acked, n = varint.decode(data[pos:])
    pos += n

    return stream_id, largest_acked, pos


def decode_frame(data):
    if len(data) < 1:
        return None, None, 0

    frame_type, n = varint.decode(data)
    pos = n

    if frame_type == FRAME_STREAM:
        stream_id, offset, payload, consumed = decode_stream(data[pos:])
        return FRAME_STREAM, (stream_id, offset, payload), pos + consumed

    elif frame_type == FRAME_ACK:
        stream_id, largest_acked, consumed = decode_ack(data[pos:])
        return FRAME_ACK, (stream_id, largest_acked), pos + consumed

    else:
        return frame_type, None, pos
