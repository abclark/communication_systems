# client.py
import socket
import struct
import threading
import sys

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
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((HOST, PORT))
        print(f"Connected to server at {HOST}:{PORT}. Type 'quit' to exit.", flush=True)

        receiver = threading.Thread(target=receive_handler, args=(client_socket,))
        receiver.daemon = True
        receiver.start()

        while True:
            message_to_send = input() 
            if message_to_send.lower() == 'quit':
                break
            
            if receiver.is_alive():
                send_message(client_socket, message_to_send)
            else:
                break

    except ConnectionRefusedError:
        print("Connection refused: Is the server running?", flush=True)
    except Exception as e:
        print(f"An error occurred: {e}", flush=True)
    finally:
        print("Closing client socket.", flush=True)
        client_socket.close()

if __name__ == "__main__":
    main()