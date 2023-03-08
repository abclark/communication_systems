#!/usr/bin/env python3
"""
BGP Finite State Machine Demo

Demonstrates the BGP peer session establishment process
as defined in RFC 4271.
"""

import sys
import time
sys.path.insert(0, '.')
from src.fsm import BGPPeer

def print_header(text):
    """Print a visually distinct section header."""
    print(f"\n{'─' * 50}")
    print(f"  {text}")
    print(f"{'─' * 50}\n")

def print_event(event):
    """Print an event being triggered."""
    print(f"  ⚡ Event: {event}")

def demo_happy_path():
    """
    Demonstrate successful BGP session establishment.

    Two peers go through:
    IDLE → CONNECT → OPENSENT → OPENCONFIRM → ESTABLISHED
    """
    print_header("BGP Session Establishment (Happy Path)")

    print("  Creating two BGP peers...")
    peer_a = BGPPeer("10.0.0.1")
    peer_b = BGPPeer("10.0.0.2")

    # Disable hold timer for clean demo (won't expire during demo)
    peer_a.hold_time = 60
    peer_b.hold_time = 60

    time.sleep(0.5)

    # Step 1: Start
    print_header("Step 1: Administrative Start")
    print_event("Start")
    peer_a.handle_event("Start")
    peer_b.handle_event("Start")
    time.sleep(0.8)

    # Step 2: TCP Connection
    print_header("Step 2: TCP Connection Established")
    print_event("TcpConnectionSuccess")
    peer_a.handle_event("TcpConnectionSuccess")
    peer_b.handle_event("TcpConnectionSuccess")
    time.sleep(0.8)

    # Step 3: OPEN Message
    print_header("Step 3: Exchange OPEN Messages")
    print("  Peers exchange: AS number, Hold Time, Router ID")
    print_event("ValidBGPOpenMessage")
    peer_a.handle_event("ValidBGPOpenMessage")
    peer_b.handle_event("ValidBGPOpenMessage")
    time.sleep(0.8)

    # Step 4: KEEPALIVE
    print_header("Step 4: Exchange KEEPALIVE Messages")
    print("  Confirms both sides are ready")
    print_event("BGPKeepaliveMessage")
    peer_a.handle_event("BGPKeepaliveMessage")
    peer_b.handle_event("BGPKeepaliveMessage")
    time.sleep(0.5)

    print_header("✓ Sessions Established!")
    print(f"  Peer A ({peer_a.peer_ip}): {peer_a.state.name}")
    print(f"  Peer B ({peer_b.peer_ip}): {peer_b.state.name}")
    print("\n  Now peers can exchange UPDATE messages with routes.\n")

    # Cleanup
    peer_a._stop_hold_timer()
    peer_b._stop_hold_timer()

    return peer_a, peer_b

def demo_connection_failure():
    """
    Demonstrate the CONNECT ↔ ACTIVE retry loop.

    When TCP connection fails, BGP retries with exponential backoff.
    """
    print_header("Connection Failure (Retry Loop)")

    peer = BGPPeer("10.0.0.3")
    peer.connect_retry_time = 2  # Short timer for demo

    print("  Peer starts but TCP connection keeps failing...")
    print("  Watch the CONNECT ↔ ACTIVE loop:\n")

    peer.handle_event("Start")
    time.sleep(0.5)

    # Simulate connection failures
    for i in range(2):
        time.sleep(1)
        print_event("TcpConnectionFails")
        peer.handle_event("TcpConnectionFails")
        time.sleep(1.5)

    print(f"\n  (In production, this continues until connection succeeds")
    print(f"   or admin intervention)\n")

    # Cleanup
    peer._stop_connect_retry_timer()

def demo_invalid_open():
    """
    Demonstrate handling of invalid OPEN message.

    If OPEN message has bad parameters (wrong AS, bad hold time),
    peer sends NOTIFICATION and returns to IDLE.
    """
    print_header("Invalid OPEN Message (Error Handling)")

    peer = BGPPeer("10.0.0.4")

    print("  Peer establishes TCP, but receives bad OPEN...\n")

    peer.handle_event("Start")
    time.sleep(0.5)
    peer.handle_event("TcpConnectionSuccess")
    time.sleep(0.5)

    print("  ⚠ Received OPEN with wrong AS number!")
    print_event("InvalidBGPOpenMessage")
    peer.handle_event("InvalidBGPOpenMessage")

    print(f"\n  Peer returns to IDLE, sends NOTIFICATION to remote.\n")

    # Cleanup
    peer._stop_connect_retry_timer()

def main():
    print("\n" + "═" * 50)
    print("  BGP FINITE STATE MACHINE DEMO")
    print("  RFC 4271 - Border Gateway Protocol")
    print("═" * 50)

    demo_happy_path()
    time.sleep(1)

    demo_connection_failure()
    time.sleep(1)

    demo_invalid_open()

    print_header("Demo Complete")
    print("  The BGP FSM ensures reliable session establishment")
    print("  between autonomous systems across the internet.\n")

if __name__ == "__main__":
    main()
