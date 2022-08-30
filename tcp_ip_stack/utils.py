import struct
import socket

def calculate_checksum(data):
    if len(data) % 2 == 1:
        data += b'\x00'
        
    s = 0
    for i in range(0, len(data), 2):
        word = (data[i] << 8) + data[i+1]
        s += word
        
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
        
    checksum = ~s & 0xFFFF
    
    return checksum

def calculate_udp_checksum(src_ip, dest_ip, udp_packet):
    src_ip_bytes = socket.inet_aton(src_ip)
    dest_ip_bytes = socket.inet_aton(dest_ip)
    reserved = 0
    protocol = 17
    udp_length = len(udp_packet)
    
    pseudo_header = struct.pack('!4s4sBBH',
        src_ip_bytes,
        dest_ip_bytes,
        reserved,
        protocol,
        udp_length
    )
    
    full_data = pseudo_header + udp_packet
    
    return calculate_checksum(full_data)
