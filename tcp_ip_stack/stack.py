import sys
import socket
import struct
from fcntl import ioctl

PF_SYSTEM = 32
SYSPROTO_CONTROL = 2
AF_SYS_CONTROL = 2
CTLIOCGINFO = 0xc0644e03
UTUN_CONTROL_NAME = b"com.apple.net.utun_control"

class TunDevice:
    def __init__(self):
        print("TunDevice: __init__ called.")
        self.sock = None
        self.ctl_id = None
        self.utun_name = None

        try:
            self.sock = socket.socket(PF_SYSTEM, socket.SOCK_DGRAM, SYSPROTO_CONTROL)
            print(f"  [INIT] System socket created (FD: {self.sock.fileno()}).")
        except OSError as e:
            print(f"  [ERROR] Failed to create system socket: {e}", file=sys.stderr)
            print("  Hint: Running with 'sudo' is usually required for system-level operations.", file=sys.stderr)
            raise

        ctl_info_request = struct.pack('I96s', 0, UTUN_CONTROL_NAME)
        try:
            ctl_info_response = ioctl(self.sock, CTLIOCGINFO, ctl_info_request)
            
            self.ctl_id, _ = struct.unpack('I96s', ctl_info_response)
            print(f"  [INIT] Resolved '{UTUN_CONTROL_NAME.decode()}' to kernel control ID: {self.ctl_id}.")
        except OSError as e:
            print(f"  [ERROR] ioctl for CTLIOCGINFO failed: {e}", file=sys.stderr)
            print("  Hint: Ensure the 'utun' kernel module is functional on your macOS system.", file=sys.stderr)
            self.close()
            raise

        try:
            self.sock.connect((self.ctl_id, 0))
            print(f"  [INIT] Successfully connected socket to utun control. Kernel will assign 'utunX'.")
        except OSError as e:
            print(f"  [ERROR] Failed to connect to utun control service: {e}", file=sys.stderr)
            print("  Hint: Check if too many utun interfaces are already active or if permissions are incorrect.", file=sys.stderr)
            self.close()
            raise
        
        print("TunDevice: __init__ completed. A new 'utunX' interface should now exist.")
        print("  ACTION: Please check 'ifconfig' in a new terminal to identify the new 'utunX' interface (e.g., utun0, utun1).")

    def read(self, size=2048):
        if not self.sock:
            return b''

        try:
            raw_data = self.sock.recv(size + 4)
        except OSError as e:
            print(f"TunDevice: Error during socket recv: {e}", file=sys.stderr)
            return b''

        if not raw_data:
            return b''

        if len(raw_data) >= 4:
            protocol_family = struct.unpack('!I', raw_data[:4])[0]
            
            if protocol_family == 2:
                return raw_data[4:]
            elif protocol_family == 30:
                return b''
            else:
                return b''
        
        return b''

    def write(self, packet_bytes):
        print("TunDevice: write() called.")
        pass

    def close(self):
        print("TunDevice: close() called.")
        pass


if __name__ == '__main__':
    print("--- Starting Stack Skeleton ---")
    tun = None
    try:
        tun = TunDevice()
        print("Stack is running (Press Ctrl+C to stop)...")
        
        print("\n--- ACTION REQUIRED ---")
        print("1. Find the name of the new utun interface by running: 'ifconfig' in a separate terminal.")
        print("2. Configure it: 'sudo ifconfig utunX 10.0.0.1 10.0.0.1 netmask 255.255.255.0 up'")
        print("3. Send a test packet to it: 'ping -c 1 10.0.0.1'")
        print("------------------------------------------------------------------\n")

        while True:
            packet = tun.read()
            if packet:
                print("--- RAW IP PACKET RECEIVED ---")
                print(packet.hex())
                print(f"Packet Length: {len(packet)} bytes\n")
            
    except KeyboardInterrupt:
        print("\n--- Ctrl+C detected. ---")
    except Exception as e:
        print(f"--- An error occurred: {e} ---", file=sys.stderr)
    finally:
        if tun:
            tun.close()
        print("--- Stack shut down. ---")
