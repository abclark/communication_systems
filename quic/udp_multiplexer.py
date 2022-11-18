import sys
sys.path.insert(0, '../tcp_ip_stack')

from stack import TunDevice
from packet_headers import IPHeader, UDPHeader
import protocols

UDP_PORT = 9000


def main():
    tun = TunDevice()

    print("\nListening for UDP on port 9000...")
    print("Configure: sudo ifconfig utun<X> 10.0.0.1 10.0.0.1 netmask 255.255.255.0 up")
    print("Test: echo -e '\\x01hello' | nc -u 10.0.0.1 9000\n")

    while True:
        packet_bytes = tun.read()
        if packet_bytes:
            ip_header = IPHeader.from_bytes(packet_bytes)
            if ip_header.protocol == protocols.PROTO_UDP:
                udp_bytes = packet_bytes[ip_header.ihl * 4:]
                udp_header = UDPHeader.from_bytes(udp_bytes)

                if udp_header.dest_port == UDP_PORT:
                    payload = udp_header.payload
                    if len(payload) >= 1:
                        stream_id = payload[0]
                        data = payload[1:].decode('utf-8', errors='replace').strip()
                        print(f"[Stream {stream_id}] Data: {data}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nDone.")
