import json
import struct

def send_message(sock, data_dict):
    message_json = json.dumps(data_dict)
    message_bytes = message_json.encode('utf-8')
    length_prefix = struct.pack('>I', len(message_bytes))
    try:
        sock.sendall(length_prefix + message_bytes)
        return True
    except (BrokenPipeError, ConnectionResetError):
        return False

def receive_message(sock):
    try:
        raw_length = sock.recv(4)
        if not raw_length: return None
        message_length = struct.unpack('>I', raw_length)[0]
        full_message = bytearray()
        while len(full_message) < message_length:
            remaining_bytes = message_length - len(full_message)
            chunk = sock.recv(min(4096, remaining_bytes))
            if not chunk: return None
            full_message.extend(chunk)
        return json.loads(full_message.decode('utf-8'))
    except (ConnectionResetError, BrokenPipeError, struct.error, json.JSONDecodeError):
        return None
