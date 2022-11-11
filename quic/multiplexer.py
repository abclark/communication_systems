import sys
sys.path.insert(0, '../tcp_ip_stack')

from stack import TunDevice
from packet_headers import IPHeader, TCPHeader
import protocols

STREAM_PORTS = [9001, 9002, 9003]

def main():
    tun = TunDevice()

    print("\nListening for TCP on ports 9001, 9002, 9003...")
    print("Configure: sudo ifconfig utun<X> 10.0.0.1 10.0.0.1 netmask 255.255.255.0 up")
    print("Test: nc 10.0.0.1 9001\n")

    while True:
        packet_bytes = tun.read()
        if packet_bytes:
            ip_header = IPHeader.from_bytes(packet_bytes)
            if ip_header.protocol == protocols.PROTO_TCP:
                tcp_bytes = packet_bytes[ip_header.ihl * 4:]
                tcp_header = TCPHeader.from_bytes(tcp_bytes)

                if tcp_header.dest_port in STREAM_PORTS:
                    print(f"Port {tcp_header.dest_port}: {tcp_header}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nDone.")
