import sys
import random

sys.path.insert(0, '../tcp_ip_stack')
from packet_headers import IPHeader, TCPHeader
import protocols

class TCPConnection:
    def __init__(self, key, isn, ack):
        self.key = key
        self.state = 'SYN_RECEIVED'
        self.my_seq_num = isn
        self.my_ack_num = ack

    def establish(self):
        self.state = 'ESTABLISHED'
        self.my_seq_num += 1

tcp_connections = {}

def handle_tcp_packet(tun, ip_header, tcp_bytes):
    try:
        tcp_header = TCPHeader.from_bytes(tcp_bytes)
        print("--- PARSED TCP HEADER ---")
        print(tcp_header)
        
        payload_len = len(tcp_header.payload)
        if payload_len > 0:
            print(f"   >>> Data: {tcp_header.payload.decode('utf-8', errors='replace')}")

        conn_key = (ip_header.src_ip, tcp_header.src_port, ip_header.dest_ip, tcp_header.dest_port)
        
        if (tcp_header.flags & protocols.TCP_FLAG_SYN) and not (tcp_header.flags & protocols.TCP_FLAG_ACK): 
            print("   >>> Received SYN. Sending SYN-ACK...")
            
            my_isn = random.randint(0, 2**32 - 1)
            their_ack_num = tcp_header.seq_num + 1

            # Create new connection object
            conn = TCPConnection(conn_key, my_isn, their_ack_num)
            tcp_connections[conn_key] = conn

            send_tcp_packet(tun, ip_header, tcp_header, conn.my_seq_num, conn.my_ack_num, protocols.TCP_FLAG_SYN | protocols.TCP_FLAG_ACK)

        elif conn_key in tcp_connections:
            conn = tcp_connections[conn_key]

            if (tcp_header.flags & protocols.TCP_FLAG_ACK) and conn.state == 'SYN_RECEIVED':
                print("   >>> Received ACK. Connection ESTABLISHED.")
                conn.establish()

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

            # --- Teardown: FIN ---
            if (tcp_header.flags & protocols.TCP_FLAG_FIN):
                print("   >>> Received FIN. Sending ACK + FIN...")
                
                # FIN consumes 1 sequence number
                conn.my_ack_num = tcp_header.seq_num + payload_len + 1
                
                # Send ACK to confirm their FIN
                # AND send our own FIN to close our side
                # Flags: FIN | ACK
                send_tcp_packet(tun, ip_header, tcp_header, conn.my_seq_num, conn.my_ack_num, protocols.TCP_FLAG_FIN | protocols.TCP_FLAG_ACK)
                
                # Our FIN consumes 1 sequence number
                conn.my_seq_num += 1
                conn.state = 'LAST_ACK'

            # --- Teardown: Final ACK ---
            elif (tcp_header.flags & protocols.TCP_FLAG_ACK) and conn.state == 'LAST_ACK':
                print("   >>> Received Final ACK. Connection CLOSED.")
                del tcp_connections[conn_key]

        # 3. Unknown Connection (Closed/Listen State) - RFC 793
        else:
            # If the state is CLOSED (i.e., data came for an unknown connection)
            # An incoming segment not containing a RST causes a RST to be sent in response.
            if not (tcp_header.flags & protocols.TCP_FLAG_RST):
                print("   >>> Unknown connection. Sending RST...")
                
                if tcp_header.flags & protocols.TCP_FLAG_ACK:
                    rst_seq = tcp_header.ack_num
                    rst_ack = 0
                    rst_flags = protocols.TCP_FLAG_RST
                else:
                    rst_seq = 0
                    rst_ack = tcp_header.seq_num + payload_len
                    # Consume phantom bytes
                    if tcp_header.flags & protocols.TCP_FLAG_SYN:
                        rst_ack += 1
                    if tcp_header.flags & protocols.TCP_FLAG_FIN:
                        rst_ack += 1
                    rst_flags = protocols.TCP_FLAG_RST | protocols.TCP_FLAG_ACK

                send_tcp_packet(tun, ip_header, tcp_header, rst_seq, rst_ack, rst_flags)

    except ValueError as e:
        print(f"Error parsing TCP message: {e}", file=sys.stderr)

def send_tcp_packet(tun, ip_header, incoming_tcp, seq, ack, flags, payload=b''):
    reply_tcp = TCPHeader(
        src_port=incoming_tcp.dest_port,
        dest_port=incoming_tcp.src_port,
        seq_num=seq,
        ack_num=ack,
        flags=flags,
        window=65535,
        checksum=0,
        urgent_ptr=0,
        payload=payload
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
        protocol=protocols.PROTO_TCP,
        checksum=0,
        src_ip=ip_header.dest_ip,
        dest_ip=ip_header.src_ip
    )
    reply_ip_bytes = reply_ip.to_bytes()

    tun.write(reply_ip_bytes + reply_tcp_bytes)
