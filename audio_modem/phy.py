import numpy as np
import threading
import queue

SAMPLE_RATE = 44100
FREQ_0 = 1000
FREQ_1 = 2000
BAUD_RATE = 100
BIT_DURATION = 1.0 / BAUD_RATE
SAMPLES_PER_BIT = int(SAMPLE_RATE * BIT_DURATION)

PREAMBLE = bytes([0xAA, 0xAA])
SYNC_WORD = bytes([0xDE, 0xAD])
HEADER = PREAMBLE + SYNC_WORD


def crc8(data):
    """CRC-8: x^8 + x^2 + x + 1"""
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ 0x07
            else:
                crc <<= 1
            crc &= 0xFF
    return crc


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
    length_and_payload = bytes([len(payload)]) + payload
    checksum = crc8(length_and_payload)
    frame = HEADER + length_and_payload + bytes([checksum])
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

    crc_offset = payload_offset + payload_length * samples_per_byte
    crc_samples = recording[crc_offset:crc_offset + samples_per_byte]
    received_crc = decode_byte(crc_samples)

    length_and_payload = bytes([payload_length]) + payload
    expected_crc = crc8(length_and_payload)

    if received_crc != expected_crc:
        return None

    return payload


class AudioDevice:
    def __init__(self):
        import sounddevice as sd
        self.sd = sd
        self.padding_samples = int(0.5 * SAMPLE_RATE)
        self.rx_queue = queue.Queue()
        self.receiving = False
        self.rx_thread = None

    def start_receiving(self):
        self.receiving = True
        self.rx_thread = threading.Thread(target=self._rx_loop)
        self.rx_thread.start()

    def stop_receiving(self):
        self.receiving = False
        if self.rx_thread:
            self.rx_thread.join()

    def _rx_loop(self):
        chunk_duration = 5
        while self.receiving:
            num_samples = int(chunk_duration * SAMPLE_RATE)
            recording = self.sd.rec(num_samples, samplerate=SAMPLE_RATE, channels=1, dtype='float32')
            self.sd.wait()
            if not self.receiving:
                break
            recording = recording.flatten()
            try:
                packet = decode_frame(recording)
                if packet is not None:
                    self.rx_queue.put(packet)
            except:
                pass

    def write(self, packet_bytes):
        frame = encode_frame(packet_bytes)
        silence = np.zeros(self.padding_samples, dtype=np.float32)
        wave = np.concatenate([silence, frame, silence])
        self.sd.play(wave, SAMPLE_RATE)
        self.sd.wait()

    def read(self, timeout=10):
        num_samples = int(timeout * SAMPLE_RATE)
        recording = self.sd.rec(num_samples, samplerate=SAMPLE_RATE, channels=1, dtype='float32')
        self.sd.wait()
        recording = recording.flatten()
        return decode_frame(recording)

    def close(self):
        pass
