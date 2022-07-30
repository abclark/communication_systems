import sys
import time
sys.path.insert(0, '.')
from src.fsm import BGPPeer

# --- Simulation Functions ---

def simulate_connect_retry_failure():
    print("\n\n--- Starting BGP Simulation (Connect Retry Failure Path) ---", flush=True)
    peer_c = BGPPeer("192.168.1.3")
    peer_c.connect_retry_time = 2 # Use a slightly shorter time for faster cycles

    peer_c.handle_event("Start") # Peer C starts, transitions to CONNECT, starts ConnectRetryTimer

    print(f"Waiting for a few cycles of CONNECT <-> ACTIVE transitions...", flush=True)
    time.sleep(7) # Shortened for faster testing

    # Manually stop the timers and session to end the simulation
    print("\nStopping the looping peer...", flush=True)
    peer_c._stop_connect_retry_timer()
    peer_c._transition_to_idle() # Explicitly move to IDLE to stop

    print("\n--- Connect Retry Failure Simulation Complete ---", flush=True)

def simulate_invalid_open():
    print("\n\n--- Starting BGP Simulation (Invalid OPEN Message Path) ---", flush=True)
    peer_d = BGPPeer("192.168.1.4")

    # Go through the initial steps to get the peer to OPENSENT
    peer_d.handle_event("Start")
    peer_d.handle_event("TcpConnectionSuccess")

    # Now, simulate receiving an invalid OPEN message
    print("\nSimulating receipt of an invalid OPEN message...", flush=True)
    peer_d.handle_event("InvalidBGPOpenMessage")

    # We need to manually stop the ConnectRetryTimer that was started in the CONNECT state
    # because the FSM goes straight to IDLE without reaching a state where it's normally stopped.
    peer_d._stop_connect_retry_timer()

    print("\n--- Invalid OPEN Message Simulation Complete ---", flush=True)

def simulate_open_delay_timer_expires():
    print("\n\n--- Starting BGP Simulation (Open Delay Timer Expiration) ---", flush=True)
    peer_e = BGPPeer("192.168.1.5")
    peer_e.open_delay_time = 3 # Set short delay time for testing

    # Go through the initial steps to get the peer to OPENSENT
    peer_e.handle_event("Start")
    peer_e.handle_event("TcpConnectionSuccess") # This starts the OpenDelayTimer

    print(f"Waiting for Peer {peer_e.peer_ip} Open Delay Timer to expire in {peer_e.open_delay_time} seconds...", flush=True)
    time.sleep(peer_e.open_delay_time + 1) # Wait for timer to expire

    # We need to manually stop the ConnectRetryTimer that was started in the CONNECT state
    # because the FSM goes straight to IDLE without reaching a state where it's normally stopped.
    peer_e._stop_connect_retry_timer()

    print("\n--- Open Delay Timer Expiration Simulation Complete ---", flush=True)


# --- Main Execution ---

def main():
    # --- Happy Path Simulation ---
    peer_a = BGPPeer("192.168.1.1")
    peer_b = BGPPeer("192.168.1.2")

    # For testing, set short timer values
    peer_a.hold_time = 5
    peer_b.hold_time = 5
    peer_a.connect_retry_time = 3
    peer_b.connect_retry_time = 3

    print("--- Starting BGP Simulation (Happy Path) ---", flush=True)
    peer_a.handle_event("Start")
    peer_b.handle_event("Start")

    print("\n--- Simulating TCP Connection ---", flush=True)
    peer_a.handle_event("TcpConnectionSuccess")
    peer_b.handle_event("TcpConnectionSuccess")

    print("\n--- Simulating OPEN Message Exchange ---", flush=True)
    peer_a.handle_event("ValidBGPOpenMessage") 
    peer_b.handle_event("ValidBGPOpenMessage")

    print("\n--- Simulating KEEPALIVE Message Exchange ---", flush=True)
    peer_a.handle_event("BGPKeepaliveMessage")
    peer_b.handle_event("BGPKeepaliveMessage")

    print("\n--- Simulation Complete (Happy Path) ---", flush=True)

    # --- Hold Timer Failure Simulation ---
    print("\n--- Testing Autonomous HoldTimer Expiration on Peer A ---", flush=True)
    print(f"Waiting for Peer {peer_a.peer_ip} Hold Timer to expire in {peer_a.hold_time} seconds...", flush=True)
    time.sleep(peer_a.hold_time + 1) # Wait slightly longer than hold_time
    print("\n--- Autonomous HoldTimer Expiration Test Complete ---", flush=True)

    # --- Run Failure Simulations ---
    simulate_connect_retry_failure()
    simulate_invalid_open()
    simulate_open_delay_timer_expires()

    print("\n\n--- All Simulations Finished ---", flush=True)


if __name__ == "__main__":
    main()
