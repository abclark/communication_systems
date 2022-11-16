import sys
sys.path.insert(0, '../tcp_ip_stack')

import random
from stack import TunDevice
from packet_headers import IPHeader, TCPHeader
import protocols

STREAM_PORTS = {9001: 1, 9002: 2, 9003: 3}

connections = {}
next_global_seq = 1
next_to_deliver = 1
pending_messages = []
delayed_messages = []


def send_tcp(tun, src_ip, src_port, dest_ip, dest_port, seq, ack, flags):
    tcp = TCPHeader(
        src_port=src_port,
        dest_port=dest_port,
        seq_num=seq,
        ack_num=ack,
        flags=flags,
        window=65535,
        checksum=0,
        urgent_ptr=0,
        payload=b''
    )
    tcp_bytes = tcp.to_bytes(src_ip, dest_ip)

    ip = IPHeader(
        version=4,
        ihl=5,
        tos=0,
        total_length=20 + len(tcp_bytes),
        identification=0,
        flags_offset=0,
        ttl=64,
        protocol=protocols.PROTO_TCP,
        checksum=0,
        src_ip=src_ip,
        dest_ip=dest_ip
    )
    ip_bytes = ip.to_bytes()
    tun.write(ip_bytes + tcp_bytes)


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
                    conn_key = (ip_header.dest_ip, tcp_header.dest_port, ip_header.src_ip, tcp_header.src_port)
                    stream_id = STREAM_PORTS[tcp_header.dest_port]
                    is_syn = (tcp_header.flags & protocols.TCP_FLAG_SYN) and not (tcp_header.flags & protocols.TCP_FLAG_ACK)

                    if is_syn:
                        our_seq = random.randint(0, 2**32 - 1)
                        our_ack = tcp_header.seq_num + 1

                        connections[conn_key] = {
                            'our_seq': our_seq,
                            'our_ack': our_ack,
                            'stream_id': stream_id,
                            'state': 'SYN_RECEIVED'
                        }

                        send_tcp(
                            tun,
                            src_ip=ip_header.dest_ip,
                            src_port=tcp_header.dest_port,
                            dest_ip=ip_header.src_ip,
                            dest_port=tcp_header.src_port,
                            seq=our_seq,
                            ack=our_ack,
                            flags=protocols.TCP_FLAG_SYN | protocols.TCP_FLAG_ACK
                        )
                        print(f"[Stream {stream_id}] SYN received, sent SYN-ACK")

                    elif conn_key in connections:
                        conn = connections[conn_key]
                        stream_id = conn['stream_id']

                        if conn['state'] == 'SYN_RECEIVED' and (tcp_header.flags & protocols.TCP_FLAG_ACK):
                            conn['state'] = 'ESTABLISHED'
                            conn['our_seq'] += 1
                            print(f"[Stream {stream_id}] Connection established")

                        payload = tcp_header.payload
                        if payload and conn['state'] == 'ESTABLISHED':
                            global next_global_seq, next_to_deliver
                            conn['our_ack'] = tcp_header.seq_num + len(payload)
                            send_tcp(
                                tun,
                                src_ip=ip_header.dest_ip,
                                src_port=tcp_header.dest_port,
                                dest_ip=ip_header.src_ip,
                                dest_port=tcp_header.src_port,
                                seq=conn['our_seq'],
                                ack=conn['our_ack'],
                                flags=protocols.TCP_FLAG_ACK
                            )
                            data = payload.decode('utf-8', errors='replace').strip()
                            seq = next_global_seq
                            next_global_seq += 1

                            if data == "flush":
                                for msg in delayed_messages:
                                    pending_messages.append(msg)
                                    print(f"[Stream {msg[1]}] (seq {msg[0]}) RELEASED: {msg[2]}")
                                delayed_messages.clear()
                            elif stream_id == 2:
                                delayed_messages.append((seq, stream_id, data))
                                print(f"[Stream {stream_id}] (seq {seq}) DELAYED: {data}")
                            else:
                                pending_messages.append((seq, stream_id, data))
                                print(f"[Stream {stream_id}] (seq {seq}) QUEUED: {data}")

                            pending_messages.sort(key=lambda x: x[0])
                            while pending_messages and pending_messages[0][0] == next_to_deliver:
                                msg = pending_messages.pop(0)
                                print(f"[Stream {msg[1]}] (seq {msg[0]}) DELIVERED: {msg[2]}")
                                next_to_deliver += 1

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nDone.")
