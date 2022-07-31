# server.py
import socket

# --- Configuration ---
HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 65432        # Port to listen on (non-privileged ports are > 1023)

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"Server is listening on {HOST}:{PORT}...", flush=True)

    # --- 4. Accept incoming connections ---
    conn, addr = server_socket.accept()
    with conn:
        print(f"Connected by {addr}", flush=True)
        while True: # Loop to continuously receive data
            data = conn.recv(1024) # Receive up to 1024 bytes of data
            if not data: # If no data, client has disconnected
                break
            print(f"Received from client: {data.decode()}", flush=True) # Decode bytes to string
            conn.sendall(data) # Echo back the received data to the client

if __name__ == "__main__":
    main()
