import sys
from packet_headers import IPHeader, ICMPMessage
import protocols

def handle_icmp_packet(tun, ip_header, icmp_bytes):
    try:
        icmp_msg = ICMPMessage.from_bytes(icmp_bytes)
        print("--- PARSED ICMP MESSAGE ---")
        print(icmp_msg)

        if icmp_msg.type == protocols.ICMP_TYPE_ECHO_REQUEST:
            print("   >>> Sending Echo Reply...")
            
            # 1. Build Reply ICMP Message
            reply_icmp = ICMPMessage(
                type=protocols.ICMP_TYPE_ECHO_REPLY, 
                code=0, 
                checksum=0,
                identifier=icmp_msg.identifier, 
                sequence_number=icmp_msg.sequence_number, 
                payload=icmp_msg.payload
            )
            reply_icmp_bytes = reply_icmp.to_bytes()

            # 2. Build Reply IP Header
            reply_ip = IPHeader(
                version=4,
                ihl=5,
                tos=0,
                total_length=20 + len(reply_icmp_bytes),
                identification=0,
                flags_offset=0,
                ttl=64,
                protocol=protocols.PROTO_ICMP,
                checksum=0,
                src_ip=ip_header.dest_ip,
                dest_ip=ip_header.src_ip
            )
            reply_ip_bytes = reply_ip.to_bytes()

            # 3. Send
            tun.write(reply_ip_bytes + reply_icmp_bytes)
    except ValueError as e:
        print(f"Error parsing ICMP message: {e}", file=sys.stderr)
