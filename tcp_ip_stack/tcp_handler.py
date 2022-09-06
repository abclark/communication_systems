import sys
import random
import socket
from packet_headers import IPHeader, TCPHeader

tcp_connections = {}

def handle_tcp_packet(tun, ip_header, tcp_bytes):
    try:
        tcp_header = TCPHeader.from_bytes(tcp_bytes)
        print("--- PARSED TCP HEADER ---")
        print(tcp_header)
        
        if tcp_header.payload:
            print(f"   >>> Data: {tcp_header.payload.decode('utf-8', errors='replace')}")

        conn_key = (ip_header.src_ip, tcp_header.src_port, ip_header.dest_ip, tcp_header.dest_port)
        
        if (tcp_header.flags & 0x02) and not (tcp_header.flags & 0x10): 
            print("   >>> Received SYN. Sending SYN-ACK...")
            
            my_isn = random.randint(0, 2**32 - 1)
            their_ack_num = tcp_header.seq_num + 1

            tcp_connections[conn_key] = {
                'state': 'SYN_RECEIVED',
                'my_seq_num': my_isn,
                'my_ack_num': their_ack_num
            }

            reply_tcp = TCPHeader(
                src_port=tcp_header.dest_port,
                dest_port=tcp_header.src_port,
                seq_num=my_isn,
                ack_num=their_ack_num,
                flags=0x02 | 0x10,
                window=65535,
                checksum=0,
                urgent_ptr=0,
                payload=b''
            )
            reply_tcp_bytes = reply_tcp.to_bytes(ip_header.dest_ip, ip_header.src_ip) 

            reply_ip = IPHeader(
                version=4,
                ihl=5,
                tos=0,
                total_length=20 + len(reply_tcp_bytes),
                identification=0,
                flags_offset=0,
                ttl=64,
                protocol=6,
                checksum=0,
                src_ip=ip_header.dest_ip,
                dest_ip=ip_header.src_ip
            )
            reply_ip_bytes = reply_ip.to_bytes()

            tun.write(reply_ip_bytes + reply_tcp_bytes)

    except ValueError as e:
        print(f"Error parsing TCP message: {e}", file=sys.stderr)
