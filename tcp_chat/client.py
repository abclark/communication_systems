# client.py
import socket
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

def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((HOST, PORT))
        print(f"Connected to server at {HOST}:{PORT}")

        while True:
            user_input = input("Enter message (or 'quit' to exit, 'long' for test message): ")
            if user_input.lower() == 'quit':
                break
            
            message_to_send = user_input
            if user_input.lower() == 'long':
                long_test_string = "long test message designed to be significantly longer than 1024 bytes"
                message_to_send = long_test_string * 50
                print(f"Sending a long test message of {len(message_to_send)} bytes.")

            send_message(client_socket, message_to_send)
            
            received_message = receive_message(client_socket)
            if received_message is None:
                print("Server closed the connection unexpectedly.")
                break
            print(f"Received from server: {received_message}")

    except ConnectionRefusedError:
        print("Connection refused: Is the server running?")
    except struct.error:
        print("Error unpacking message length. Server might have sent malformed data or disconnected.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Closing client socket.")
        client_socket.close()

if __name__ == "__main__":
    main()
