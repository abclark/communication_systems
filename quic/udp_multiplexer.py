import sys
sys.path.insert(0, '../tcp_ip_stack')

from stack import TunDevice
from packet_headers import IPHeader, UDPHeader
import protocols

STREAM_PORTS = {9001: 1, 9002: 2, 9003: 3}


def main():
    tun = TunDevice()

    print("\nListening for UDP on ports 9001, 9002, 9003...")
    print("Configure: sudo ifconfig utun<X> 10.0.0.1 10.0.0.1 netmask 255.255.255.0 up")
    print("Test: nc -u 10.0.0.1 9001\n")

    while True:
        packet_bytes = tun.read()
        if packet_bytes:
            ip_header = IPHeader.from_bytes(packet_bytes)
            if ip_header.protocol == protocols.PROTO_UDP:
                udp_bytes = packet_bytes[ip_header.ihl * 4:]
                udp_header = UDPHeader.from_bytes(udp_bytes)

                if udp_header.dest_port in STREAM_PORTS:
                    stream_id = STREAM_PORTS[udp_header.dest_port]
                    data = udp_header.payload.decode('utf-8', errors='replace').strip()
                    print(f"[Stream {stream_id}] Data: {data}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nDone.")
