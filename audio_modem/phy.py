import numpy as np

SAMPLE_RATE = 44100
FREQ_0 = 1000
FREQ_1 = 2000
BAUD_RATE = 100
BIT_DURATION = 1.0 / BAUD_RATE
SAMPLES_PER_BIT = int(SAMPLE_RATE * BIT_DURATION)

PREAMBLE = bytes([0xAA, 0xAA])
SYNC_WORD = bytes([0xDE, 0xAD])
HEADER = PREAMBLE + SYNC_WORD


def generate_tone(frequency, duration, sample_rate=SAMPLE_RATE, amplitude=0.5):
    num_samples = int(sample_rate * duration)
    t = np.arange(num_samples) / sample_rate
    wave = amplitude * np.sin(2 * np.pi * frequency * t)
    return wave.astype(np.float32)


def encode_bit(bit):
    frequency = FREQ_1 if bit else FREQ_0
    return generate_tone(frequency, BIT_DURATION)


def encode_byte(byte_value):
    waveforms = []
    for i in range(7, -1, -1):
        bit = (byte_value >> i) & 1
        waveforms.append(encode_bit(bit))
    return np.concatenate(waveforms)


def encode_bytes(data):
    waveforms = [encode_byte(b) for b in data]
    return np.concatenate(waveforms)


def decode_bit(samples):
    spectrum = np.abs(np.fft.rfft(samples))
    freq_resolution = SAMPLE_RATE / len(samples)
    bin_0 = int(FREQ_0 / freq_resolution)
    bin_1 = int(FREQ_1 / freq_resolution)
    if spectrum[bin_1] > spectrum[bin_0]:
        return 1
    else:
        return 0


def decode_byte(samples):
    byte_value = 0
    for i in range(8):
        start = i * SAMPLES_PER_BIT
        end = start + SAMPLES_PER_BIT
        bit_samples = samples[start:end]
        bit = decode_bit(bit_samples)
        byte_value = (byte_value << 1) | bit
    return byte_value


def decode_bytes(samples, num_bytes):
    result = []
    samples_per_byte = SAMPLES_PER_BIT * 8
    for i in range(num_bytes):
        start = i * samples_per_byte
        end = start + samples_per_byte
        byte_samples = samples[start:end]
        byte_value = decode_byte(byte_samples)
        result.append(byte_value)
    return bytes(result)


def encode_frame(payload):
    if len(payload) > 255:
        raise ValueError("Payload too long (max 255 bytes)")
    frame = HEADER + bytes([len(payload)]) + payload
    return encode_bytes(frame)


def find_frame_offset(recording):
    header_signal = encode_bytes(HEADER)
    correlation = np.correlate(recording, header_signal, mode='valid')
    offset = np.argmax(np.abs(correlation))
    return offset


def decode_frame(recording):
    offset = find_frame_offset(recording)
    samples_per_byte = SAMPLES_PER_BIT * 8

    header_samples = len(HEADER) * samples_per_byte
    length_offset = offset + header_samples

    length_samples = recording[length_offset:length_offset + samples_per_byte]
    payload_length = decode_byte(length_samples)

    payload_offset = length_offset + samples_per_byte
    payload_samples = recording[payload_offset:payload_offset + payload_length * samples_per_byte]
    payload = decode_bytes(payload_samples, payload_length)

    return payload
