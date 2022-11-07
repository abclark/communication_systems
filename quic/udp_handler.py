import sys
sys.path.insert(0, '../tcp_ip_stack')
from packet_headers import IPHeader, UDPHeader
import protocols

def handle_udp_packet(tun, ip_header, udp_bytes):
    try:
        udp_header = UDPHeader.from_bytes(udp_bytes)
        print("--- PARSED UDP HEADER ---")
        print(udp_header)
        
        payload_str = udp_header.payload.decode('utf-8', errors='replace')
        print(f"   >>> Data: {payload_str}")

        print("   >>> Sending UDP Echo Reply...")

        clean_payload = payload_str.strip()
        reversed_payload = clean_payload[::-1] + "\n"
        reply_payload = reversed_payload.encode('utf-8')

        reply_udp = UDPHeader(
            src_port=udp_header.dest_port,
            dest_port=udp_header.src_port,
            length=8 + len(reply_payload),
            checksum=0,
            payload=reply_payload
        )
        
        reply_udp_bytes = reply_udp.to_bytes(
            src_ip=ip_header.dest_ip, 
            dest_ip=ip_header.src_ip
        )

        reply_ip = IPHeader(
            version=4,
            ihl=5,
            tos=0,
            total_length=20 + len(reply_udp_bytes),
            identification=0,
            flags_offset=0,
            ttl=64,
            protocol=protocols.PROTO_UDP,
            checksum=0,
            src_ip=ip_header.dest_ip,
            dest_ip=ip_header.src_ip
        )
        reply_ip_bytes = reply_ip.to_bytes()

        tun.write(reply_ip_bytes + reply_udp_bytes)

    except ValueError as e:
        print(f"Error parsing UDP message: {e}", file=sys.stderr)
