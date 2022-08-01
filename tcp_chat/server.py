# server.py
import socket
import threading

HOST = '127.0.0.1'
PORT = 65432

def client_handler(conn, addr):
    print(f"Connected by {addr}", flush=True)
    with conn:
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    break
                print(f"Received from client {addr}: {data.decode()}", flush=True)
                conn.sendall(data)
            except (ConnectionResetError, BrokenPipeError):
                break
    print(f"Client {addr} disconnected.", flush=True)

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"Server is listening on {HOST}:{PORT}...", flush=True)

    while True:
        conn, addr = server_socket.accept()
        thread = threading.Thread(target=client_handler, args=(conn, addr))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}", flush=True)

if __name__ == "__main__":
    main()
