import sys
import random
import socket
from packet_headers import IPHeader, TCPHeader

# Global dictionary to store connection state (for simplicity, a real stack would be more complex)
# Key: (dest_ip, dest_port, src_ip, src_port)
# Value: { 'state': '...', 'my_seq_num': ..., 'my_ack_num': ... }
tcp_connections = {}

def handle_tcp_packet(tun, ip_header, tcp_bytes):
    try:
        tcp_header = TCPHeader.from_bytes(tcp_bytes)
        print("--- PARSED TCP HEADER ---")
        print(tcp_header)
        
        if tcp_header.payload:
            print(f"   >>> Data: {tcp_header.payload.decode('utf-8', errors='replace')}")

        # --- TCP Handshake Logic ---
        conn_key = (ip_header.src_ip, tcp_header.src_port, ip_header.dest_ip, tcp_header.dest_port)
        
        # If SYN flag is set (first step of handshake)
        # Check if SYN (0x02) is set and ACK (0x10) is NOT set (to avoid replying to our own SYN-ACKs loops)
        if (tcp_header.flags & 0x02) and not (tcp_header.flags & 0x10): 
            print("   >>> Received SYN. Sending SYN-ACK...")
            
            # Create new connection state
            # My initial sequence number will be random
            my_isn = random.randint(0, 2**32 - 1)
            # My acknowledgment number is their sequence number + 1 (SYN consumes 1 sequence number)
            their_ack_num = tcp_header.seq_num + 1

            # Store state (for future packets on this connection)
            tcp_connections[conn_key] = {
                'state': 'SYN_RECEIVED',
                'my_seq_num': my_isn,
                'my_ack_num': their_ack_num
            }

            # Build SYN-ACK reply
            reply_tcp = TCPHeader(
                src_port=tcp_header.dest_port, # My port is their destination port
                dest_port=tcp_header.src_port, # My destination is their source port
                seq_num=my_isn,
                ack_num=their_ack_num,
                flags=0x02 | 0x10, # SYN | ACK
                window=65535,
                checksum=0, # Will be calculated by to_bytes
                urgent_ptr=0,
                payload=b''
            )
            # Serialize TCP Header
            # We must swap src/dest IP for the pseudo-header checksum calculation
            reply_tcp_bytes = reply_tcp.to_bytes(ip_header.dest_ip, ip_header.src_ip) 

            reply_ip = IPHeader(
                version=4,
                ihl=5,
                tos=0,
                total_length=20 + len(reply_tcp_bytes),
                identification=0,
                flags_offset=0,
                ttl=64,
                protocol=6, # TCP
                checksum=0, # Will be calculated by to_bytes
                src_ip=ip_header.dest_ip, # My IP is their destination IP
                dest_ip=ip_header.src_ip # My destination IP is their source IP
            )
            reply_ip_bytes = reply_ip.to_bytes()

            tun.write(reply_ip_bytes + reply_tcp_bytes)

    except ValueError as e:
        print(f"Error parsing TCP message: {e}", file=sys.stderr)
