import socket
import threading
import sys
import ssl
import os
import json
import base64
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import protocol

class ChatClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.my_id = None
        self.k_group = None
        self.other_clients_pubkeys = {}
        self.registration_complete = threading.Event()
        self.private_key = None
        self.public_key = None
        self.sock = None
        self.receiver_thread = None
        self.message_handlers = {
            "chat_encrypted": self._handle_encrypted_chat,
            "notification": self._handle_notification,
            "new_user_joined": self._handle_new_user,
            "group_key_distribution": self._handle_key_distribution
        }

    def _generate_keys(self):
        print("Generating ephemeral key pair for this session...")
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()
        print("Key pair generated.")

    def _receive_handler(self):
        while True:
            msg_dict = protocol.receive_message(self.sock)
            if msg_dict is None:
                print("\rConnection to server lost. Press Enter to exit.", flush=True)
                self.registration_complete.set()
                os._exit(1)

            if not self.registration_complete.is_set():
                self._handle_registration(msg_dict)
                continue

            msg_type = msg_dict.get("type")
            handler = self.message_handlers.get(msg_type)
            
            if handler:
                handler(msg_dict)
            else:
                self._handle_unhandled(msg_dict)

    def _handle_registration(self, msg_dict):
        if msg_dict.get("type") == "registration_success":
            self.my_id = msg_dict.get("id")
            print(f"Registered with server as User {self.my_id}.", flush=True)
            if self.my_id == 1:
                print("This client is the group leader. Generating group key...", flush=True)
                self.k_group = os.urandom(32)
            self.registration_complete.set()
        else:
            print(f"Expected registration_success message, but got {msg_dict.get('type')}. Exiting.", flush=True)
            self.registration_complete.set()
            os._exit(1)

    def _handle_encrypted_chat(self, msg_dict):
        display_message = ""
        if self.k_group:
            try:
                sender_id = msg_dict.get("sender_id")
                nonce = base64.b64decode(msg_dict.get("nonce"))
                ciphertext = base64.b64decode(msg_dict.get("ciphertext"))
                
                aesgcm = AESGCM(self.k_group)
                decrypted_content = aesgcm.decrypt(nonce, ciphertext, None).decode('utf-8')
                display_message = f"[User {sender_id}] {decrypted_content}"
            except Exception:
                display_message = f"[DECRYPTION ERROR from User {sender_id}]"
        else:
            display_message = "[Message received, but I don't have the group key to decrypt it yet.]"
        print(f"\r{display_message}\nEnter message: ", end="", flush=True)

    def _handle_notification(self, msg_dict):
        display_message = f"[{msg_dict.get('content')}]"
        print(f"\r{display_message}\nEnter message: ", end="", flush=True)

    def _handle_new_user(self, msg_dict):
        if self.my_id != 1: return
        user_id = msg_dict.get("id")
        pubkey_pem = msg_dict.get("pubkey")
        print(f"\r[SERVER] New user {user_id} joined. Distributing group key...", flush=True)
        
        new_pub_key = serialization.load_pem_public_key(pubkey_pem.encode('utf-8'))
        self.other_clients_pubkeys[user_id] = new_pub_key
        
        encrypted_k_group = new_pub_key.encrypt(self.k_group, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
        encoded_key = base64.b64encode(encrypted_k_group).decode('utf-8')

        key_dist_msg = {"type": "group_key_distribution", "recipient_id": user_id, "key": encoded_key}
        protocol.send_message(self.sock, key_dist_msg)
        display_message = f"[Sent group key to User {user_id}]"
        print(f"\r{display_message}\nEnter message: ", end="", flush=True)

    def _handle_key_distribution(self, msg_dict):
        if msg_dict.get("recipient_id") == self.my_id:
            print("\r[SERVER] Received encrypted group key from leader.", flush=True)
            encoded_key = msg_dict.get("key")
            encrypted_k_group = base64.b64decode(encoded_key)
            self.k_group = self.private_key.decrypt(encrypted_k_group, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
            display_message = "[Group key received and decrypted successfully!]"
            print(f"\r{display_message}\nEnter message: ", end="", flush=True)

    def _handle_unhandled(self, msg_dict):
        display_message = f"[UNHANDLED] {msg_dict}"
        print(f"\r{display_message}\nEnter message: ", end="", flush=True)

    def start(self):
        self._generate_keys()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        cert_path = os.path.join(script_dir, 'ssl', 'cert.pem')
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=cert_path)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_REQUIRED
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock = context.wrap_socket(client_socket, server_hostname=self.host)

        try:
            self.sock.connect((self.host, self.port))
            print(f"Connected to secure server at {self.host}:{self.port}.", flush=True)

            self.receiver_thread = threading.Thread(target=self._receive_handler)
            self.receiver_thread.daemon = True
            self.receiver_thread.start()

            public_key_pem = self.public_key.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo).decode('utf-8')
            registration_message = {"type": "register", "pubkey": public_key_pem}
            protocol.send_message(self.sock, registration_message)
            self.registration_complete.wait()

            if self.my_id is None:
                print("Client registration failed. Exiting.", flush=True)
                return

            while True:
                message_to_send = input("Enter message: ")
                if message_to_send.lower() == 'quit': break
                
                if self.receiver_thread.is_alive():
                    if self.k_group:
                        nonce = os.urandom(12)
                        aesgcm = AESGCM(self.k_group)
                        encrypted_content = aesgcm.encrypt(nonce, message_to_send.encode('utf-8'), None)
                        chat_message = {"type": "chat_encrypted", "nonce": base64.b64encode(nonce).decode('utf-8'), "ciphertext": base64.b64encode(encrypted_content).decode('utf-8')}
                        protocol.send_message(self.sock, chat_message)
                    else:
                        print("Cannot send message: group key not yet established.", flush=True)
                else:
                    break
        except ConnectionRefusedError:
            print("Connection refused: Is the server running?", flush=True)
        except Exception as e:
            print(f"An error occurred: {e}", flush=True)
        finally:
            print("Closing client socket.", flush=True)
            if self.sock: self.sock.close()

if __name__ == "__main__":
    HOST = '127.0.0.1'
    PORT = 65432
    client = ChatClient(HOST, PORT)
    client.start()