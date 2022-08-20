import struct
import socket

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

    def __repr__(self):
        return (f"IPv{self.version} (len={self.total_length} bytes) "
                f"from {self.src_ip} to {self.dest_ip} "
                f"[Proto={self.protocol} TTL={self.ttl}]")

class ICMPMessage:
    def __init__(self, type, code, checksum, identifier, sequence_number, payload):
        self.type = type # ICMP message type (e.g., 8 for Echo Request, 0 for Echo Reply)
        self.code = code # ICMP message code (e.g., 0 for Echo Request/Reply)
        self.checksum = checksum # ICMP checksum
        self.identifier = identifier # Used to match requests with replies
        self.sequence_number = sequence_number # Used to match requests with replies
        self.payload = payload # The actual data carried by the ICMP message (e.g., ping data)


    @classmethod
    def from_bytes(cls, icmp_bytes):
        """
        Parses raw bytes into an ICMPMessage object.
        """
        if len(icmp_bytes) < 8:
            raise ValueError("ICMP message is too short to contain a basic header (min 8 bytes).")

        # Unpack the first 8 bytes of the ICMP header
        # ! = Network (Big Endian)
        # B = 1 byte (Type, Code)
        # H = 2 bytes (Checksum, Identifier, Sequence Number)
        icmp_header_tuple = struct.unpack('!BBHHH', icmp_bytes[:8])

        icmp_type = icmp_header_tuple[0]
        icmp_code = icmp_header_tuple[1]
        icmp_checksum = icmp_header_tuple[2]
        icmp_identifier = icmp_header_tuple[3]
        icmp_sequence_number = icmp_header_tuple[4]

        # The rest of the bytes are the ICMP payload
        icmp_payload = icmp_bytes[8:]

        return cls(icmp_type, icmp_code, icmp_checksum, icmp_identifier, icmp_sequence_number, icmp_payload)

    def __repr__(self):
        return (f"ICMP(Type={self.type}, Code={self.code}, "
                f"ID={self.identifier}, Seq={self.sequence_number}, "
                f"PayloadLen={len(self.payload)} bytes)")