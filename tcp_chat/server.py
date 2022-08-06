# server.py
import socket
import threading
import struct
import time
import ssl
import os
import json
from cryptography.hazmat.primitives import serialization

HOST = '127.0.0.1'
PORT = 65432

clients = {}
client_id_counter = 0
clients_lock = threading.Lock()

def send_message(sock, data_dict):
    message_json = json.dumps(data_dict)
    message_bytes = message_json.encode('utf-8')
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
        
        return json.loads(full_message.decode('utf-8'))
    except (ConnectionResetError, BrokenPipeError, struct.error, json.JSONDecodeError):
        return None

def broadcast(message_dict, sender_id):
    with clients_lock:
        for client_id, client_info in list(clients.items()):
            if client_id != sender_id:
                if not send_message(client_info["socket"], message_dict):
                    del clients[client_id]
                    client_info["socket"].close()
                    print(f"Removed disconnected client User {client_id} during broadcast.", flush=True)

def client_handler(conn, addr):
    global client_id_counter
    client_id = None
    
    try:
        initial_message = receive_message(conn)
        if initial_message is None or initial_message.get("type") != "register":
            return

        public_key_pem = initial_message.get("pubkey")
        if not public_key_pem:
            return

        public_key = serialization.load_pem_public_key(public_key_pem.encode('utf-8'))

        with clients_lock:
            client_id_counter += 1
            client_id = client_id_counter
            clients[client_id] = {"socket": conn, "pubkey": public_key}
        
        print(f"Client {addr} registered as User {client_id}", flush=True)

        notification = {"type": "notification", "content": f"User {client_id} has joined the chat!"}
        broadcast(notification, None)
        print(f"Broadcasting: {notification['content']}", flush=True)

        if client_id > 1:
            with clients_lock:
                leader_info = clients.get(1)
            if leader_info:
                leader_notification = {
                    "type": "new_user_joined",
                    "id": client_id,
                    "pubkey": public_key_pem
                }
                send_message(leader_info["socket"], leader_notification)

        while True:
            msg_dict = receive_message(conn)
            if msg_dict is None:
                break
            
            if msg_dict.get("type") == "chat":
                broadcast_dict = {
                    "type": "chat_message",
                    "sender_id": client_id,
                    "content": msg_dict.get("content", "")
                }
                print(f"Broadcasting from User {client_id}: {msg_dict.get('content')}", flush=True)
                broadcast(broadcast_dict, client_id)
            
    finally:
        with clients_lock:
            if client_id and client_id in clients:
                del clients[client_id]
        
        if client_id:
            notification = {"type": "notification", "content": f"User {client_id} has left the chat."}
            broadcast(notification, None)
            print(f"Broadcasting: {notification['content']}", flush=True)
        
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
