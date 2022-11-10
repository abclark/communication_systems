import sys
import random

sys.path.insert(0, '../tcp_ip_stack')
from packet_headers import IPHeader, TCPHeader
import protocols

class TCPConnection:
    def __init__(self, src_ip, src_port, dest_ip, dest_port):
        self.src_ip = src_ip
        self.src_port = src_port
        self.dest_ip = dest_ip
        self.dest_port = dest_port
        self.my_seq_num = 0
        self.my_ack_num = 0
        self.state = 'CLOSED'

    @property
    def key(self):
        return (self.src_ip, self.src_port, self.dest_ip, self.dest_port)

tcp_connections = {}

def tcp_connect(tun, src_ip, src_port, dest_ip, dest_port):
    conn = TCPConnection(src_ip, src_port, dest_ip, dest_port)
    conn.my_seq_num = random.randint(0, 2**32 - 1)
    conn.state = 'SYN_SENT'
    tcp_connections[conn.key] = conn

    print(f"   >>> Sending SYN to {dest_ip}:{dest_port}...")
    send_tcp_raw(tun, src_ip, src_port, dest_ip, dest_port,
                 conn.my_seq_num, 0, protocols.TCP_FLAG_SYN)
    return conn

def handle_tcp_packet(tun, ip_header, tcp_bytes):
    try:
        tcp_header = TCPHeader.from_bytes(tcp_bytes)
        print("--- PARSED TCP HEADER ---")
        print(tcp_header)
        
        payload_len = len(tcp_header.payload)
        if payload_len > 0:
            print(f"   >>> Data: {tcp_header.payload.decode('utf-8', errors='replace')}")

        conn_key = (ip_header.dest_ip, tcp_header.dest_port, ip_header.src_ip, tcp_header.src_port)
        
        if (tcp_header.flags & protocols.TCP_FLAG_SYN) and not (tcp_header.flags & protocols.TCP_FLAG_ACK):
            print("   >>> Received SYN. Sending SYN-ACK...")

            conn = TCPConnection(
                ip_header.dest_ip,
                tcp_header.dest_port,
                ip_header.src_ip,
                tcp_header.src_port
            )
            conn.my_seq_num = random.randint(0, 2**32 - 1)
            conn.my_ack_num = tcp_header.seq_num + 1
            conn.state = 'SYN_RECEIVED'
            tcp_connections[conn.key] = conn

            send_tcp_packet(tun, ip_header, tcp_header, conn.my_seq_num, conn.my_ack_num, protocols.TCP_FLAG_SYN | protocols.TCP_FLAG_ACK)

        elif conn_key in tcp_connections:
            conn = tcp_connections[conn_key]

            if (tcp_header.flags & protocols.TCP_FLAG_ACK) and conn.state == 'SYN_RECEIVED':
                print("   >>> Received ACK. Connection ESTABLISHED.")
                conn.state = 'ESTABLISHED'
                conn.my_seq_num += 1

            if (tcp_header.flags & protocols.TCP_FLAG_SYN) and (tcp_header.flags & protocols.TCP_FLAG_ACK) and conn.state == 'SYN_SENT':
                print("   >>> Received SYN-ACK. Sending ACK...")
                conn.my_seq_num += 1
                conn.my_ack_num = tcp_header.seq_num + 1
                conn.state = 'ESTABLISHED'
                send_tcp_packet(tun, ip_header, tcp_header, conn.my_seq_num, conn.my_ack_num, protocols.TCP_FLAG_ACK)
                print("   >>> Connection ESTABLISHED.")

            if payload_len > 0:
                print(f"   >>> Received {payload_len} bytes. Sending ACK...")
                
                conn.my_ack_num = tcp_header.seq_num + payload_len
                
                payload_str = tcp_header.payload.decode('utf-8', errors='replace')
                clean_payload = payload_str.strip()
                print(f"   Message: {clean_payload}")
                reply = input("   Reply: ")
                reply_payload = (reply + "\n").encode('utf-8')
                
                print(f"   >>> Sending: {reply}")

                send_tcp_packet(tun, ip_header, tcp_header, conn.my_seq_num, conn.my_ack_num, protocols.TCP_FLAG_PSH | protocols.TCP_FLAG_ACK, reply_payload)
                
                conn.my_seq_num += len(reply_payload)

            if (tcp_header.flags & protocols.TCP_FLAG_FIN):
                print("   >>> Received FIN. Sending ACK + FIN...")
                conn.my_ack_num = tcp_header.seq_num + payload_len + 1
                send_tcp_packet(tun, ip_header, tcp_header, conn.my_seq_num, conn.my_ack_num, protocols.TCP_FLAG_FIN | protocols.TCP_FLAG_ACK)
                conn.my_seq_num += 1
                conn.state = 'LAST_ACK'

            elif (tcp_header.flags & protocols.TCP_FLAG_ACK) and conn.state == 'LAST_ACK':
                print("   >>> Received Final ACK. Connection CLOSED.")
                del tcp_connections[conn_key]

        else:
            if not (tcp_header.flags & protocols.TCP_FLAG_RST):
                print("   >>> Unknown connection. Sending RST...")

                if tcp_header.flags & protocols.TCP_FLAG_ACK:
                    rst_seq = tcp_header.ack_num
                    rst_ack = 0
                    rst_flags = protocols.TCP_FLAG_RST
                else:
                    rst_seq = 0
                    rst_ack = tcp_header.seq_num + payload_len
                    if tcp_header.flags & protocols.TCP_FLAG_SYN:
                        rst_ack += 1
                    if tcp_header.flags & protocols.TCP_FLAG_FIN:
                        rst_ack += 1
                    rst_flags = protocols.TCP_FLAG_RST | protocols.TCP_FLAG_ACK

                send_tcp_packet(tun, ip_header, tcp_header, rst_seq, rst_ack, rst_flags)

    except ValueError as e:
        print(f"Error parsing TCP message: {e}", file=sys.stderr)

def send_tcp_raw(tun, src_ip, src_port, dest_ip, dest_port, seq, ack, flags, payload=b''):
    tcp = TCPHeader(
        src_port=src_port,
        dest_port=dest_port,
        seq_num=seq,
        ack_num=ack,
        flags=flags,
        window=65535,
        checksum=0,
        urgent_ptr=0,
        payload=payload
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


def send_tcp_packet(tun, ip_header, incoming_tcp, seq, ack, flags, payload=b''):
    send_tcp_raw(
        tun,
        src_ip=ip_header.dest_ip,
        src_port=incoming_tcp.dest_port,
        dest_ip=ip_header.src_ip,
        dest_port=incoming_tcp.src_port,
        seq=seq,
        ack=ack,
        flags=flags,
        payload=payload
    )
