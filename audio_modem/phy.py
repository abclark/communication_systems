import time
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


def generate_tone(frequency, duration, sample_rate=SAMPLE_RATE, amplitude=1.0):
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


def find_frame_offset(recording, min_correlation=0.1):
    header_signal = encode_bytes(HEADER)
    correlation = np.correlate(recording, header_signal, mode='valid')
    abs_correlation = np.abs(correlation)
    offset = np.argmax(abs_correlation)
    peak = abs_correlation[offset]

    # Normalize by the energy of the header signal
    header_energy = np.sum(header_signal ** 2)
    normalized_peak = peak / header_energy

    if normalized_peak < min_correlation:
        return None  # No significant signal detected

    return offset


def decode_frame(recording):
    """Returns (payload, samples_consumed) or (None, 0)."""
    offset = find_frame_offset(recording)
    if offset is None:
        return (None, 0)

    samples_per_byte = SAMPLES_PER_BIT * 8

    header_samples = len(HEADER) * samples_per_byte
    length_offset = offset + header_samples

    if length_offset + samples_per_byte > len(recording):
        return (None, 0)

    length_samples = recording[length_offset:length_offset + samples_per_byte]
    payload_length = decode_byte(length_samples)

    if payload_length == 0:
        return (None, 0)

    payload_offset = length_offset + samples_per_byte
    crc_offset = payload_offset + payload_length * samples_per_byte
    frame_end = crc_offset + samples_per_byte

    if frame_end > len(recording):
        return (None, 0)

    payload_samples = recording[payload_offset:crc_offset]
    payload = decode_bytes(payload_samples, payload_length)

    crc_samples = recording[crc_offset:frame_end]
    received_crc = decode_byte(crc_samples)

    length_and_payload = bytes([payload_length]) + payload
    expected_crc = crc8(length_and_payload)

    if received_crc != expected_crc:
        return (None, 0)

    return (payload, frame_end)


class AudioDevice:
    def __init__(self):
        import sounddevice as sd
        self.sd = sd
        self.padding_samples = int(0.5 * SAMPLE_RATE)
        self.rx_queue = queue.Queue()
        self.buffer = np.array([], dtype=np.float32)
        self.buffer_lock = threading.Lock()
        self.stream = None
        self.running = False
        self.scan_thread = None

    def _audio_callback(self, indata, frames, time, status):
        with self.buffer_lock:
            self.buffer = np.append(self.buffer, indata.flatten())

    def _scan_loop(self):
        max_buffer_samples = SAMPLE_RATE * 20
        min_frame_samples = SAMPLES_PER_BIT * 8 * 6

        while self.running:
            time.sleep(1.0)

            with self.buffer_lock:
                if len(self.buffer) < min_frame_samples:
                    continue
                buffer_copy = self.buffer.copy()

            payload, consumed = decode_frame(buffer_copy)

            with self.buffer_lock:
                if payload is not None:
                    self.rx_queue.put(payload)
                    self.buffer = self.buffer[consumed:]
                elif len(self.buffer) > max_buffer_samples:
                    self.buffer = self.buffer[-max_buffer_samples:]

    def start_receiving(self):
        self.running = True
        with self.buffer_lock:
            self.buffer = np.array([], dtype=np.float32)
        self.stream = self.sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='float32',
            callback=self._audio_callback
        )
        self.stream.start()
        self.scan_thread = threading.Thread(target=self._scan_loop)
        self.scan_thread.start()

    def stop_receiving(self):
        self.running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        if self.scan_thread:
            self.scan_thread.join()
            self.scan_thread = None

    def write(self, packet_bytes):
        was_running = self.running
        self.stop_receiving()

        frame = encode_frame(packet_bytes)
        silence = np.zeros(self.padding_samples, dtype=np.float32)
        wave = np.concatenate([silence, frame, silence])
        self.sd.play(wave, SAMPLE_RATE)
        self.sd.wait()

        if was_running:
            self.start_receiving()

    def read(self, timeout=None):
        return self.rx_queue.get(timeout=timeout)

    def close(self):
        self.stop_receiving()
