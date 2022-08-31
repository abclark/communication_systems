import struct
import socket
from utils import calculate_checksum

class IPHeader:
    def __init__(self, version, ihl, tos, total_length, identification, flags_offset, ttl, protocol, checksum, src_ip, dest_ip):
        self.version = version
        self.ihl = ihl
        self.tos = tos
        self.total_length = total_length
        self.identification = identification
        self.flags_offset = flags_offset
        self.ttl = ttl
        self.protocol = protocol
        self.checksum = checksum
        self.src_ip = src_ip
        self.dest_ip = dest_ip

    @classmethod
    def from_bytes(cls, packet_bytes):
        if len(packet_bytes) < 20:
            raise ValueError("Packet is too short to contain an IPv4 header.")

        header_tuple = struct.unpack('!BBHHHBBH4s4s', packet_bytes[:20])

        ver_ihl = header_tuple[0]
        version = ver_ihl >> 4
        ihl = ver_ihl & 0x0F
        
        tos = header_tuple[1]
        total_length = header_tuple[2]
        identification = header_tuple[3]
        flags_offset = header_tuple[4]
        ttl = header_tuple[5]
        protocol = header_tuple[6]
        checksum = header_tuple[7]
        src_ip_bytes = header_tuple[8]
        dest_ip_bytes = header_tuple[9]

        src_ip_str = socket.inet_ntoa(src_ip_bytes)
        dest_ip_str = socket.inet_ntoa(dest_ip_bytes)

        return cls(version, ihl, tos, total_length, identification, flags_offset, ttl, protocol, checksum, src_ip_str, dest_ip_str)

    def to_bytes(self):
        ver_ihl = (self.version << 4) + self.ihl
        
        src_ip_bytes = socket.inet_aton(self.src_ip)
        dest_ip_bytes = socket.inet_aton(self.dest_ip)
        
        header_without_checksum = struct.pack('!BBHHHBBH4s4s',
            ver_ihl,
            self.tos,
            self.total_length,
            self.identification,
            self.flags_offset,
            self.ttl,
            self.protocol,
            0,
            src_ip_bytes,
            dest_ip_bytes
        )
        
        self.checksum = calculate_checksum(header_without_checksum)
        
        header_with_checksum = struct.pack('!BBHHHBBH4s4s',
            ver_ihl,
            self.tos,
            self.total_length,
            self.identification,
            self.flags_offset,
            self.ttl,
            self.protocol,
            self.checksum,
            src_ip_bytes,
            dest_ip_bytes
        )
        
        return header_with_checksum

    def __repr__(self):
        return (f"IPv{self.version} (len={self.total_length} bytes) "
                f"from {self.src_ip} to {self.dest_ip} "
                f"[Proto={self.protocol} TTL={self.ttl}]")

class ICMPMessage:
    def __init__(self, type, code, checksum, identifier, sequence_number, payload):
        self.type = type
        self.code = code
        self.checksum = checksum
        self.identifier = identifier
        self.sequence_number = sequence_number
        self.payload = payload

    @classmethod
    def from_bytes(cls, icmp_bytes):
        if len(icmp_bytes) < 8:
            raise ValueError("ICMP message is too short to contain a basic header (min 8 bytes).")

        icmp_header_tuple = struct.unpack('!BBHHH', icmp_bytes[:8])

        icmp_type = icmp_header_tuple[0]
        icmp_code = icmp_header_tuple[1]
        icmp_checksum = icmp_header_tuple[2]
        icmp_identifier = icmp_header_tuple[3]
        icmp_sequence_number = icmp_header_tuple[4]

        icmp_payload = icmp_bytes[8:]

        return cls(icmp_type, icmp_code, icmp_checksum, icmp_identifier, icmp_sequence_number, icmp_payload)

    def to_bytes(self):
        header_without_checksum = struct.pack('!BBHHH', 
            self.type, 
            self.code, 
            0,
            self.identifier, 
            self.sequence_number
        )
        
        checksum_input = header_without_checksum + self.payload
        self.checksum = calculate_checksum(checksum_input)
        
        header_with_checksum = struct.pack('!BBHHH', 
            self.type, 
            self.code, 
            self.checksum, 
            self.identifier, 
            self.sequence_number
        )
        
        return header_with_checksum + self.payload

    def __repr__(self):
        return (f"ICMP(Type={self.type}, Code={self.code}, "
                f"ID={self.identifier}, Seq={self.sequence_number}, "
                f"PayloadLen={len(self.payload)} bytes)")

class UDPHeader:
    def __init__(self, src_port, dest_port, length, checksum, payload):
        self.src_port = src_port
        self.dest_port = dest_port
        self.length = length
        self.checksum = checksum
        self.payload = payload

    @classmethod
    def from_bytes(cls, udp_bytes):
        if len(udp_bytes) < 8:
            raise ValueError("UDP packet is too short to contain a header (min 8 bytes).")

        header_tuple = struct.unpack('!HHHH', udp_bytes[:8])
        
        src_port = header_tuple[0]
        dest_port = header_tuple[1]
        length = header_tuple[2]
        checksum = header_tuple[3]
        
        payload = udp_bytes[8:]
        
        return cls(src_port, dest_port, length, checksum, payload)

    def to_bytes(self, src_ip, dest_ip):
        """
        Serializes the UDPHeader object into bytes, calculating the checksum.
        Requires IP addresses for the Pseudo-Header.
        """
        # Pack the header with a zero checksum initially
        # ! = Network (Big Endian)
        header_without_checksum = struct.pack('!HHHH',
            self.src_port,
            self.dest_port,
            self.length,
            0 # Checksum set to 0 for calculation
        )
        
        # Combine Header + Payload for checksumming
        udp_packet = header_without_checksum + self.payload
        
        # Calculate UDP Checksum (Pseudo-Header + UDP Header + Payload)
        self.checksum = calculate_udp_checksum(src_ip, dest_ip, udp_packet)
        
        # Pack the header again with the real checksum
        header_with_checksum = struct.pack('!HHHH',
            self.src_port,
            self.dest_port,
            self.length,
            self.checksum
        )
        
        return header_with_checksum + self.payload

    def __repr__(self):
        return (f"UDP(Src={self.src_port}, Dst={self.dest_port}, "
                f"Len={self.length}, Checksum={hex(self.checksum)})")