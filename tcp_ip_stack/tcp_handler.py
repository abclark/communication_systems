import sys
from packet_headers import IPHeader, TCPHeader

def handle_tcp_packet(tun, ip_header, tcp_bytes):
    try:
        tcp_header = TCPHeader.from_bytes(tcp_bytes)
        print("--- PARSED TCP HEADER ---")
        print(tcp_header)
        
        if tcp_header.payload:
            print(f"   >>> Data: {tcp_header.payload.decode('utf-8', errors='replace')}")

    except ValueError as e:
        print(f"Error parsing TCP message: {e}", file=sys.stderr)
