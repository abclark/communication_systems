# server.py
import socket
import threading
import struct
import time
import ssl
import os
from cryptography.hazmat.primitives import serialization

HOST = '127.0.0.1'
PORT = 65432

clients = {}
client_id_counter = 0
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

def broadcast(message, sender_id):
    with clients_lock:
        for client_id, client_info in list(clients.items()):
            if client_id != sender_id:
                if not send_message(client_info["socket"], message):
                    del clients[client_id]
                    client_info["socket"].close()
                    print(f"Removed disconnected client User {client_id} during broadcast.", flush=True)

def client_handler(conn, addr):
    global client_id_counter
    client_id = None
    
    try:
        serialized_public_key = receive_message(conn)
        if serialized_public_key is None:
            return

        public_key = serialization.load_pem_public_key(serialized_public_key.encode())

        with clients_lock:
            client_id_counter += 1
            client_id = client_id_counter
            clients[client_id] = {"socket": conn, "pubkey": public_key}
        
        print(f"Client {addr} registered as User {client_id}", flush=True)

        broadcast_message = f"User {client_id} has joined the chat!"
        broadcast(broadcast_message, None)
        print(broadcast_message, flush=True)

        while True:
            received_message = receive_message(conn)
            if received_message is None:
                break
            
            full_message_to_broadcast = f"[User {client_id}] {received_message}"
            print(f"Broadcasting from User {client_id}: {received_message}", flush=True)
            broadcast(full_message_to_broadcast, client_id)
            
    finally:
        with clients_lock:
            if client_id and client_id in clients:
                del clients[client_id]
        
        if client_id:
            broadcast_message = f"User {client_id} has left the chat."
            broadcast(broadcast_message, None)
            print(broadcast_message, flush=True)
        
        conn.close()
        print(f"Client {addr} (User {client_id}) handler finished.", flush=True)


def main():
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
