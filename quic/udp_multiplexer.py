import sys
sys.path.insert(0, '../tcp_ip_stack')

from stack import TunDevice
from packet_headers import IPHeader, UDPHeader
import protocols

UDP_PORT = 9000

PACKET_DATA = 0x01
PACKET_ACK = 0x02

stream_next_deliver = {1: 1, 2: 1, 3: 1}
stream_pending = {1: [], 2: [], 3: []}
delayed_messages = []


def send_udp(tun, src_ip, src_port, dest_ip, dest_port, payload):
    udp = UDPHeader(
        src_port=src_port,
        dest_port=dest_port,
        length=8 + len(payload),
        checksum=0,
        payload=payload
    )
    udp_bytes = udp.to_bytes(src_ip, dest_ip)

    ip = IPHeader(
        version=4,
        ihl=5,
        tos=0,
        total_length=20 + len(udp_bytes),
        identification=0,
        flags_offset=0,
        ttl=64,
        protocol=protocols.PROTO_UDP,
        checksum=0,
        src_ip=src_ip,
        dest_ip=dest_ip
    )
    ip_bytes = ip.to_bytes()
    tun.write(ip_bytes + udp_bytes)


def main():
    tun = TunDevice()

    print("\nListening for UDP on port 9000...")
    print("Configure: sudo ifconfig utun<X> 192.168.100.1 192.168.100.2 netmask 255.255.255.0 up")
    print("Packet format: [type 1B][stream 1B][seq 2B][data...]")
    print("  DATA=0x01, ACK=0x02")
    input("\nPress Enter after configuring interface...")

    while True:
        packet_bytes = tun.read()
        if packet_bytes:
            ip_header = IPHeader.from_bytes(packet_bytes)
            if ip_header.protocol == protocols.PROTO_UDP:
                udp_bytes = packet_bytes[ip_header.ihl * 4:]
                udp_header = UDPHeader.from_bytes(udp_bytes)

                if udp_header.dest_port == UDP_PORT:
                    payload = udp_header.payload
                    if len(payload) < 4:
                        continue

                    packet_type = payload[0]
                    stream_id = payload[1]
                    seq = int.from_bytes(payload[2:4], 'big')

                    if stream_id not in stream_next_deliver:
                        continue

                    if packet_type == PACKET_DATA:
                        data = payload[4:].decode('utf-8', errors='replace').strip()
                        print(f"[Stream {stream_id}] (seq {seq}) DATA: {data}")

                        ack_payload = bytes([PACKET_ACK, stream_id]) + seq.to_bytes(2, 'big')
                        send_udp(tun, ip_header.dest_ip, UDP_PORT, ip_header.src_ip, udp_header.src_port, ack_payload)
                        print(f"[Stream {stream_id}] (seq {seq}) ACK sent")

                        stream_pending[stream_id].append((seq, data))

                        stream_pending[stream_id].sort(key=lambda x: x[0])
                        while stream_pending[stream_id] and stream_pending[stream_id][0][0] == stream_next_deliver[stream_id]:
                            msg = stream_pending[stream_id].pop(0)
                            print(f"[Stream {stream_id}] (seq {msg[0]}) DELIVERED: {msg[1]}")
                            stream_next_deliver[stream_id] += 1

                    elif packet_type == PACKET_ACK:
                        print(f"[Stream {stream_id}] (seq {seq}) ACK received")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nDone.")
