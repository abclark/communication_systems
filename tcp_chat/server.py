# server.py
import socket
import threading
import struct
import time
import ssl
import os
import json
from cryptography.hazmat.primitives import serialization

class ChatServer:
    def __init__(self, host='127.0.0.1', port=65432):
        self.host = host
        self.port = port
        self.clients = {}
        self.client_id_counter = 0
        self.clients_lock = threading.Lock()
        self.server_socket = None

    def _send_message(self, sock, data_dict):
        message_json = json.dumps(data_dict)
        message_bytes = message_json.encode('utf-8')
        length_prefix = struct.pack('>I', len(message_bytes))
        try:
            sock.sendall(length_prefix + message_bytes)
            return True
        except (BrokenPipeError, ConnectionResetError):
            return False

    def _receive_message(self, sock):
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

    def _broadcast(self, message_dict, sender_id):
        with self.clients_lock:
            for client_id, client_info in list(self.clients.items()):
                if client_id != sender_id:
                    if not self._send_message(client_info["socket"], message_dict):
                        del self.clients[client_id]
                        client_info["socket"].close()
                        print(f"Removed disconnected client User {client_id} during broadcast.", flush=True)

    def _client_handler(self, conn, addr):
        client_id = None
        try:
            initial_message = self._receive_message(conn)
            if initial_message is None or initial_message.get("type") != "register": return

            public_key_pem = initial_message.get("pubkey")
            if not public_key_pem: return

            public_key = serialization.load_pem_public_key(public_key_pem.encode('utf-8'))

            with self.clients_lock:
                self.client_id_counter += 1
                client_id = self.client_id_counter
                self.clients[client_id] = {"socket": conn, "pubkey": public_key}
            
            print(f"Client {addr} registered as User {client_id}", flush=True)
            self._send_message(conn, {"type": "registration_success", "id": client_id})

            notification = {"type": "notification", "content": f"User {client_id} has joined the chat!"}
            self._broadcast(notification, None)
            print(f"Broadcasting: {notification['content']}", flush=True)

            if client_id > 1:
                with self.clients_lock:
                    leader_info = self.clients.get(1)
                if leader_info:
                    leader_notification = {"type": "new_user_joined", "id": client_id, "pubkey": public_key_pem}
                    self._send_message(leader_info["socket"], leader_notification)

            while True:
                msg_dict = self._receive_message(conn)
                if msg_dict is None: break
                
                msg_type = msg_dict.get("type")
                if msg_type == "chat_encrypted":
                    msg_dict["sender_id"] = client_id
                    print(f"Relaying encrypted message from User {client_id}", flush=True)
                    self._broadcast(msg_dict, client_id)
                elif msg_type == "group_key_distribution":
                    recipient_id = msg_dict.get("recipient_id")
                    with self.clients_lock:
                        recipient_info = self.clients.get(recipient_id)
                    if recipient_info:
                        print(f"Relaying group key from User {client_id} to User {recipient_id}", flush=True)
                        self._send_message(recipient_info["socket"], msg_dict)
        finally:
            with self.clients_lock:
                if client_id and client_id in self.clients:
                    del self.clients[client_id]
            if client_id:
                notification = {"type": "notification", "content": f"User {client_id} has left the chat."}
                self._broadcast(notification, None)
                print(f"Broadcasting: {notification['content']}", flush=True)
            conn.close()
            print(f"Client {addr} (User {client_id}) handler finished.", flush=True)

    def start(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        cert_path = os.path.join(script_dir, 'ssl', 'cert.pem')
        key_path = os.path.join(script_dir, 'ssl', 'key.pem')

        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile=cert_path, keyfile=key_path)

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen()
        print(f"Server is listening on {self.host}:{self.port}...", flush=True)
        self.server_socket = context.wrap_socket(server_socket, server_side=True)

        try:
            while True:
                conn, addr = self.server_socket.accept()
                thread = threading.Thread(target=self._client_handler, args=(conn, addr))
                thread.daemon = True
                thread.start()
                with self.clients_lock:
                    print(f"[ACTIVE CONNECTIONS] {len(self.clients) + 1}", flush=True)
        except KeyboardInterrupt:
            print("Server shutting down gracefully...", flush=True)
        finally:
            if self.server_socket: self.server_socket.close()
            print("Server stopped.", flush=True)

if __name__ == "__main__":
    server = ChatServer()
    server.start()
