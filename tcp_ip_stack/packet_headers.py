class IPHeader:
    """
    Represents an IPv4 Header.
    """
    def __init__(self):
        """Initializes the IPHeader object."""
        print("IPHeader: __init__ called.")
        pass

    @classmethod
    def from_bytes(cls, packet_bytes):
        """Parses raw bytes into an IPHeader object."""
        print("IPHeader: from_bytes called.")
        pass

    def __repr__(self):
        """String representation for printing the IPHeader object."""
        print("IPHeader: __repr__ called.")
        pass