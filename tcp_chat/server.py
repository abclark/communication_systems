# server.py
import socket
import threading
import struct

HOST = '127.0.0.1'
PORT = 65432

def send_message(sock, message):
    message_bytes = message.encode()
    length_prefix = struct.pack('>I', len(message_bytes))
    sock.sendall(length_prefix + message_bytes)

def receive_message(sock):
    raw_length = sock.recv(4)
    if not raw_length:
        return None
    
    message_length = struct.unpack('>I', raw_length)[0]
    
    full_message = bytearray()
    while len(full_message) < message_length:
        remaining_bytes = message_length - len(full_message)
        chunk = sock.recv(min(4096, remaining_bytes))
        if not chunk:
            return None
        full_message.extend(chunk)
    
    return full_message.decode()

def client_handler(conn, addr):
    print(f"Connected by {addr}", flush=True)
    with conn:
        while True:
            try:
                received_message = receive_message(conn)
                if received_message is None:
                    break
                
                print(f"Received from client {addr}: {received_message}", flush=True)
                send_message(conn, received_message)
                
            except (ConnectionResetError, BrokenPipeError, struct.error):
                break
    print(f"Client {addr} disconnected.", flush=True)

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"Server is listening on {HOST}:{PORT}...", flush=True)

    while True:
        conn, addr = server_socket.accept()
        thread = threading.Thread(target=client_handler, args=(conn, addr))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}", flush=True)

if __name__ == "__main__":
    main()
