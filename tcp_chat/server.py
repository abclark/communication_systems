# server.py
import socket
import threading
import struct
import time
import ssl
import os

HOST = '127.0.0.1'
PORT = 65432

clients = []
clients_lock = threading.Lock()

def send_message(sock, message):
    message_bytes = message.encode()
    length_prefix = struct.pack('>I', len(message_bytes))
    try:
        sock.sendall(length_prefix + message_bytes)
    except (BrokenPipeError, ConnectionResetError):
        return False
    return True

def receive_message(sock):
    try:
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
    except (ConnectionResetError, BrokenPipeError, struct.error):
        return None

def broadcast(message, sender_conn):
    with clients_lock:
        for client_conn in list(clients):
            if client_conn != sender_conn:
                if not send_message(client_conn, message):
                    clients.remove(client_conn)
                    print(f"Removed disconnected client during broadcast.", flush=True)

def client_handler(conn, addr):
    with clients_lock:
        clients.append(conn)
    
    broadcast_message = f"User {addr} has joined the chat!"
    broadcast(broadcast_message, None)
    print(broadcast_message, flush=True)

    try:
        while True:
            received_message = receive_message(conn)
            if received_message is None:
                break
            
            full_message_to_broadcast = f"[{addr}] {received_message}"
            print(f"Broadcasting: {full_message_to_broadcast}", flush=True)
            broadcast(full_message_to_broadcast, conn)
            
    finally:
        with clients_lock:
            if conn in clients:
                clients.remove(conn)
        
        broadcast_message = f"User {addr} has left the chat."
        broadcast(broadcast_message, None)
        print(broadcast_message, flush=True)
        conn.close()
        
    print(f"Client {addr} handler finished.", flush=True)


def main():
    # Get the absolute path to the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cert_path = os.path.join(script_dir, 'ssl', 'cert.pem')
    key_path = os.path.join(script_dir, 'ssl', 'key.pem')

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=cert_path, keyfile=key_path)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"Server is listening on {HOST}:{PORT}...", flush=True)

    secure_server_socket = context.wrap_socket(server_socket, server_side=True)

    try:
        while True:
            conn, addr = secure_server_socket.accept()
            thread = threading.Thread(target=client_handler, args=(conn, addr))
            thread.daemon = True
            thread.start()
            with clients_lock:
                print(f"[ACTIVE CONNECTIONS] {len(clients)}", flush=True)
    except KeyboardInterrupt:
        print("Server shutting down gracefully...", flush=True)
    finally:
        secure_server_socket.close()
        print("Server stopped.", flush=True)

if __name__ == "__main__":
    main()
