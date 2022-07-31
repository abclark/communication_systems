# client.py
import socket

# --- Configuration (must match server) ---
HOST = '127.0.0.1'
PORT = 65432

def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try: # Use a try-except block to catch connection errors
        client_socket.connect((HOST, PORT))
        print(f"Successfully connected to server at {HOST}:{PORT}", flush=True)

        message = "Hello, server! This is the client."
        client_socket.sendall(message.encode()) # Encode string to bytes before sending
        print(f"Sent to server: {message}", flush=True)

        data = client_socket.recv(1024) # Receive echoed data from server
        print(f"Received from server: {data.decode()}", flush=True) # Decode bytes to string

    except ConnectionRefusedError:
        print(f"Connection refused. Is the server running on {HOST}:{PORT}?", flush=True)
    except Exception as e:
        print(f"An error occurred: {e}", flush=True)
    finally:
        client_socket.close()
        print("Connection closed.", flush=True)


if __name__ == "__main__":
    main()