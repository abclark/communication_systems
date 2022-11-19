import sys
sys.path.insert(0, '../tcp_ip_stack')

from stack import TunDevice
from packet_headers import IPHeader, UDPHeader
import protocols

UDP_PORT = 9000

stream_seqs = {1: 1, 2: 1, 3: 1}
stream_next_deliver = {1: 1, 2: 1, 3: 1}
stream_pending = {1: [], 2: [], 3: []}
delayed_messages = []


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

                        if stream_id not in stream_seqs:
                            continue

                        seq = stream_seqs[stream_id]
                        stream_seqs[stream_id] += 1

                        if data == "flush":
                            for msg in delayed_messages:
                                s_id, s_seq, s_data = msg
                                stream_pending[s_id].append((s_seq, s_data))
                                print(f"[Stream {s_id}] (seq {s_seq}) RELEASED: {s_data}")
                            delayed_messages.clear()
                        elif stream_id == 2:
                            delayed_messages.append((stream_id, seq, data))
                            print(f"[Stream {stream_id}] (seq {seq}) DELAYED: {data}")
                        else:
                            stream_pending[stream_id].append((seq, data))
                            print(f"[Stream {stream_id}] (seq {seq}) QUEUED: {data}")

                        for s_id in stream_pending:
                            stream_pending[s_id].sort(key=lambda x: x[0])
                            while stream_pending[s_id] and stream_pending[s_id][0][0] == stream_next_deliver[s_id]:
                                msg = stream_pending[s_id].pop(0)
                                print(f"[Stream {s_id}] (seq {msg[0]}) DELIVERED: {msg[1]}")
                                stream_next_deliver[s_id] += 1


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nDone.")
