import socket
import struct
import threading
import sys
import ssl
import os
import json
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

HOST = '127.0.0.1'
PORT = 65432

my_id = None
k_group = None
other_clients_pubkeys = {}
registration_complete = threading.Event()

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

def receive_handler(sock):
    global my_id, k_group

    while True:
        msg_dict = receive_message(sock)
        if msg_dict is None:
            print("\rConnection to server lost. Press Enter to exit.", flush=True)
            registration_complete.set()
            os._exit(1)

        msg_type = msg_dict.get("type")

        if not registration_complete.is_set():
            if msg_type == "registration_success":
                my_id = msg_dict.get("id")
                print(f"Registered with server as User {my_id}.", flush=True)
                if my_id == 1:
                    print("This client is the group leader. Generating group key...", flush=True)
                    k_group = os.urandom(32)
                registration_complete.set()
            else:
                print(f"Expected registration_success message, but got {msg_type}. Exiting.", flush=True)
                registration_complete.set()
                os._exit(1)
            continue

        if msg_type == "chat_message":
            sender_id = msg_dict.get("sender_id")
            content = msg_dict.get("content")
            display_message = f"[User {sender_id}] {content}"
        elif msg_type == "notification":
            display_message = f"[{msg_dict.get('content')}]"
        elif msg_type == "new_user_joined":
            user_id = msg_dict.get("id")
            display_message = f"[SERVER] New user {user_id} joined. Received their public key. (Key distribution not yet implemented)"
        else:
            display_message = f"[UNHANDLED] {msg_dict}"
        
        print(f"\r{display_message}\nEnter message: ", end="", flush=True)

def main():
    global my_id, k_group
    print("Generating ephemeral key pair for this session...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_key = private_key.public_key()
    print("Key pair generated.")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    cert_path = os.path.join(script_dir, 'ssl', 'cert.pem')

    context = ssl.create_default_context(
        ssl.Purpose.SERVER_AUTH, cafile=cert_path)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_REQUIRED

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    secure_sock = context.wrap_socket(client_socket, server_hostname=HOST)

    try:
        secure_sock.connect((HOST, PORT))
        print(f"Connected to secure server at {HOST}:{PORT}.", flush=True)

        receiver = threading.Thread(target=receive_handler, args=(secure_sock,))
        receiver.daemon = True
        receiver.start()

        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        registration_message = {
            "type": "register",
            "pubkey": public_key_pem
        }
        send_message(secure_sock, registration_message)
        
        registration_complete.wait()

        if my_id is None:
            print("Client registration failed. Exiting.", flush=True)
            return

        while True:
            message_to_send = input("Enter message: ") 
            if message_to_send.lower() == 'quit':
                break
            
            if receiver.is_alive():
                chat_message = {
                    "type": "chat",
                    "content": message_to_send
                }
                send_message(secure_sock, chat_message)
            else:
                break

    except ConnectionRefusedError:
        print("Connection refused: Is the server running?", flush=True)
    except ssl.SSLCertVerificationError as e:
        print(f"Certificate verification error: {e}", flush=True)
        print("Ensure the client trusts the server's certificate.", flush=True)
    except Exception as e:
        print(f"An error occurred: {e}", flush=True)
    finally:
        print("Closing client socket.", flush=True)
        secure_sock.close()

if __name__ == "__main__":
    main()