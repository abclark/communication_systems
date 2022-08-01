# client.py
import socket

HOST = '127.0.0.1'
PORT = 65432

def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((HOST, PORT))
        print(f"Connected to server at {HOST}:{PORT}")

        while True:
            message = input("Enter message (or 'quit' to exit): ")
            if message.lower() == 'quit':
                break
            
            client_socket.sendall(message.encode())
            data = client_socket.recv(1024)
            if not data:
                print("Server closed the connection unexpectedly.")
                break
            print(f"Received from server: {data.decode()}")

    except ConnectionRefusedError:
        print("Connection refused: Is the server running?")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Closing client socket.")
        client_socket.close()

if __name__ == "__main__":
    main()