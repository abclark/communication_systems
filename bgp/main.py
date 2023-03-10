#!/usr/bin/env python3
"""BGP FSM Demo - simulates peer session establishment."""

import sys
import time
sys.path.insert(0, '.')
from src.fsm import BGPPeer

def pause():
    input("\n[Press Enter to continue...]")
    print()

def main():
    print("=== BGP FSM Demo ===\n")

    # Create two peers
    peer_a = BGPPeer("10.0.0.1")
    peer_b = BGPPeer("10.0.0.2")
    peer_a.hold_time = 60  # Long hold time so it doesn't expire during demo
    peer_b.hold_time = 60

    # --- Happy path: IDLE -> CONNECT -> OPENSENT -> OPENCONFIRM -> ESTABLISHED ---
    print("--- Starting peers ---")
    peer_a.handle_event("Start")
    peer_b.handle_event("Start")
    time.sleep(0.3)

    print("\n--- TCP connects ---")
    peer_a.handle_event("TcpConnectionSuccess")
    peer_b.handle_event("TcpConnectionSuccess")
    time.sleep(0.3)

    print("\n--- OPEN messages exchanged ---")
    peer_a.handle_event("ValidBGPOpenMessage")
    peer_b.handle_event("ValidBGPOpenMessage")
    time.sleep(0.3)

    print("\n--- KEEPALIVE messages exchanged ---")
    peer_a.handle_event("BGPKeepaliveMessage")
    peer_b.handle_event("BGPKeepaliveMessage")
    time.sleep(0.3)

    print(f"\nFinal states: peer_a={peer_a.state.name}, peer_b={peer_b.state.name}")

    # Cleanup
    peer_a._stop_hold_timer()
    peer_b._stop_hold_timer()

    pause()

    # --- Connection failure scenario ---
    print("=== Connection Failure Scenario ===\n")
    peer_c = BGPPeer("10.0.0.3")
    peer_c.connect_retry_time = 2

    peer_c.handle_event("Start")
    time.sleep(0.3)

    print("\n--- TCP connection fails ---")
    peer_c.handle_event("TcpConnectionFails")
    time.sleep(0.3)
    peer_c.handle_event("TcpConnectionFails")

    print(f"\nPeer oscillates between CONNECT and ACTIVE until connection succeeds")
    peer_c._stop_connect_retry_timer()

    pause()

    # --- Invalid OPEN scenario ---
    print("=== Invalid OPEN Scenario ===\n")
    peer_d = BGPPeer("10.0.0.4")

    peer_d.handle_event("Start")
    peer_d.handle_event("TcpConnectionSuccess")
    time.sleep(0.3)

    print("\n--- Received OPEN with wrong AS number ---")
    peer_d.handle_event("InvalidBGPOpenMessage")

    print(f"\nPeer returns to IDLE after sending NOTIFICATION")
    peer_d._stop_connect_retry_timer()

    print("\n=== Demo complete ===")

if __name__ == "__main__":
    main()
