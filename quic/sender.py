import socket
import time

DEST_IP = '192.168.100.100'
UDP_PORT = 9000

PACKET_DATA = 0x01
PACKET_ACK = 0x02

pending_acks = {}


def send_data(sock, stream_id, seq, data):
    payload = bytes([PACKET_DATA, stream_id]) + seq.to_bytes(2, 'big') + data.encode('utf-8')
    sock.sendto(payload, (DEST_IP, UDP_PORT))
    pending_acks[(stream_id, seq)] = (time.time(), data)
    print(f"[Stream {stream_id}] (seq {seq}) SENT: {data}")


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)

    print("\nSender starting...")
    print("Make sure receiver is running first.")
    print(f"Sending to {DEST_IP}:{UDP_PORT}\n")

    send_data(sock, stream_id=1, seq=1, data="hello")
    send_data(sock, stream_id=1, seq=2, data="world")

    timeout_seconds = 2.0

    while pending_acks:
        try:
            payload, addr = sock.recvfrom(1024)
            if len(payload) >= 4 and payload[0] == PACKET_ACK:
                stream_id = payload[1]
                seq = int.from_bytes(payload[2:4], 'big')

                key = (stream_id, seq)
                if key in pending_acks:
                    del pending_acks[key]
                    print(f"[Stream {stream_id}] (seq {seq}) ACK received")
        except BlockingIOError:
            pass

        now = time.time()
        for key, (send_time, data) in list(pending_acks.items()):
            if now - send_time > timeout_seconds:
                stream_id, seq = key
                print(f"[Stream {stream_id}] (seq {seq}) TIMEOUT, retransmitting...")
                send_data(sock, stream_id, seq, data)

    print("\nAll packets ACKed!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nDone.")
