import socket
import threading
import sys
import ssl
import os
import json
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from crypto_helper import CryptoHelper
import protocol

class ChatClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.my_id = None
        self.other_clients_pubkeys = {}
        self.registration_complete = threading.Event()
        self.private_key = None
        self.public_key = None
        self.sock = None
        self.receiver_thread = None
        self.crypto = None
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
        self.crypto = CryptoHelper(self.private_key)
        print("Key pair and crypto helper generated.")

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
                self.crypto.set_group_key(os.urandom(32))
            self.registration_complete.set()
        else:
            print(f"Expected registration_success message, but got {msg_dict.get('type')}. Exiting.", flush=True)
            self.registration_complete.set()
            os._exit(1)

    def _handle_encrypted_chat(self, msg_dict):
        display_message = ""
        sender_id = msg_dict.get("sender_id")
        nonce_b64 = msg_dict.get("nonce")
        ciphertext_b64 = msg_dict.get("ciphertext")
        
        try:
            decrypted_content = self.crypto.decrypt_chat_message(nonce_b64, ciphertext_b64)
            if decrypted_content:
                display_message = f"[User {sender_id}] {decrypted_content}"
            else:
                display_message = "[Message received, but group key is not set.]"
        except Exception:
            display_message = f"[DECRYPTION ERROR from User {sender_id}]"

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
        
        encoded_key = self.crypto.encrypt_group_key_for(self.crypto.get_group_key(), new_pub_key)

        key_dist_msg = {"type": "group_key_distribution", "recipient_id": user_id, "key": encoded_key}
        protocol.send_message(self.sock, key_dist_msg)

        display_message = f"[Sent group key to User {user_id}]"
        print(f"\r{display_message}\nEnter message: ", end="", flush=True)

    def _handle_key_distribution(self, msg_dict):
        if msg_dict.get("recipient_id") == self.my_id:
            print("\r[SERVER] Received encrypted group key from leader.", flush=True)
            encoded_key = msg_dict.get("key")
            self.crypto.decrypt_group_key(encoded_key)
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
                    nonce, ciphertext = self.crypto.encrypt_chat_message(message_to_send)
                    if nonce and ciphertext:
                        chat_message = {"type": "chat_encrypted", "nonce": nonce, "ciphertext": ciphertext}
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