# client.py
import socket
import struct
import threading
import sys
import ssl
import os

HOST = '127.0.0.1'
PORT = 65432

def send_message(sock, message):
    message_bytes = message.encode()
    length_prefix = struct.pack('>I', len(message_bytes))
    sock.sendall(length_prefix + message_bytes)

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
    except (ConnectionResetError, struct.error):
        return None

def receive_handler(sock):
    while True:
        message = receive_message(sock)
        if message is None:
            print("\rConnection to server lost. Press Enter to exit.", flush=True)
            break
        print(f"\r{message}\nEnter message: ", end="", flush=True)

def main():
    # Get the absolute path to the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cert_path = os.path.join(script_dir, 'ssl', 'cert.pem')

    # Create an SSL context that trusts our self-signed certificate
    context = ssl.create_default_context(
        ssl.Purpose.SERVER_AUTH, cafile=cert_path)
    # Since we're using a self-signed certificate with a custom hostname
    # (localhost), we may need to disable standard hostname checking.
    # For a real application, you would use a proper certificate with a
    # matching hostname.
    context.check_hostname = False
    context.verify_mode = ssl.CERT_REQUIRED


    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    secure_sock = context.wrap_socket(client_socket, server_hostname=HOST)

    try:
        secure_sock.connect((HOST, PORT))
        print(f"Connected to secure server at {HOST}:{PORT}. Type 'quit' to exit.", flush=True)

        receiver = threading.Thread(target=receive_handler, args=(secure_sock,))
        receiver.daemon = True
        receiver.start()

        while True:
            message_to_send = input() 
            if message_to_send.lower() == 'quit':
                break
            
            if receiver.is_alive():
                send_message(secure_sock, message_to_send)
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