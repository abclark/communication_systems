from enum import Enum
import threading
import time

class BGPFSMState(Enum):
    IDLE = 0
    CONNECT = 1
    ACTIVE = 2
    OPENSENT = 3
    OPENCONFIRM = 4
    ESTABLISHED = 5

class BGPPeer:
    def __init__(self, peer_ip):
        self.peer_ip = peer_ip
        self.state = BGPFSMState.IDLE
        
        # Timer attributes
        self.hold_time = 5
        self.hold_timer = None
        self.hold_timer_running = False
        
        self.connect_retry_time = 10
        self.connect_retry_timer = None
        self.connect_retry_timer_running = False

        self.open_delay_time = 5
        self.open_delay_timer = None
        self.open_delay_timer_running = False

    # --- Timer Management ---
    def _start_hold_timer(self):
        if self.hold_timer_running:
            self._stop_hold_timer()
        self.hold_timer = threading.Timer(self.hold_time, self.handle_event, ["HoldTimerExpires"])
        self.hold_timer.start()
        self.hold_timer_running = True
        print(f"Peer {self.peer_ip}: Hold Timer started ({self.hold_time}s).", flush=True)

    def _stop_hold_timer(self):
        if self.hold_timer_running:
            self.hold_timer.cancel()
            self.hold_timer_running = False
            print(f"Peer {self.peer_ip}: Hold Timer stopped.", flush=True)

    def _reset_hold_timer(self):
        self._start_hold_timer()
        print(f"Peer {self.peer_ip}: Hold Timer reset.", flush=True)

    def _start_connect_retry_timer(self):
        if self.connect_retry_timer_running:
            self._stop_connect_retry_timer()
        self.connect_retry_timer = threading.Timer(self.connect_retry_time, self.handle_event, ["ConnectRetryTimerExpires"])
        self.connect_retry_timer.start()
        self.connect_retry_timer_running = True
        print(f"Peer {self.peer_ip}: Connect Retry Timer started ({self.connect_retry_time}s).", flush=True)

    def _stop_connect_retry_timer(self):
        if self.connect_retry_timer_running:
            self.connect_retry_timer.cancel()
            self.connect_retry_timer_running = False
            print(f"Peer {self.peer_ip}: Connect Retry Timer stopped.", flush=True)

    def _reset_connect_retry_timer(self):
        self._start_connect_retry_timer()
        print(f"Peer {self.peer_ip}: Connect Retry Timer reset.", flush=True)

    def _start_open_delay_timer(self):
        if self.open_delay_timer_running:
            self._stop_open_delay_timer()
        self.open_delay_timer = threading.Timer(self.open_delay_time, self.handle_event, ["OpenDelayTimerExpires"])
        self.open_delay_timer.start()
        self.open_delay_timer_running = True
        print(f"Peer {self.peer_ip}: Open Delay Timer started ({self.open_delay_time}s).", flush=True)

    def _stop_open_delay_timer(self):
        if self.open_delay_timer_running:
            self.open_delay_timer.cancel()
            self.open_delay_timer_running = False
            print(f"Peer {self.peer_ip}: Open Delay Timer stopped.", flush=True)

    # --- FSM Event Handler ---
    def handle_event(self, event_type, *args, **kwargs):
        if self.state == BGPFSMState.IDLE:
            if event_type == "Start":
                self._transition_to_connect()
        
        elif self.state == BGPFSMState.CONNECT:
            if event_type == "TcpConnectionSuccess":
                self._transition_to_opensent()
            elif event_type == "ConnectRetryTimerExpires":
                self._transition_to_active()
            elif event_type == "TcpConnectionFails":
                self._transition_to_active()
        
        elif self.state == BGPFSMState.ACTIVE:
            if event_type == "TcpConnectionSuccess":
                self._transition_to_opensent()
            elif event_type == "ConnectRetryTimerExpires":
                self._transition_to_connect()
            elif event_type == "TcpConnectionFails":
                self._transition_to_connect()
        
        elif self.state == BGPFSMState.OPENSENT:
            if event_type == "ValidBGPOpenMessage":
                self._stop_open_delay_timer()
                self._transition_to_confirm()
            elif event_type == "InvalidBGPOpenMessage":
                self._stop_open_delay_timer()
                self._transition_to_idle()
            elif event_type == "TcpConnectionFails":
                self._transition_to_active()
            elif event_type == "OpenDelayTimerExpires":
                self._transition_to_idle()
            elif event_type == "BGPNotification":
                self._transition_to_idle()
        
        elif self.state == BGPFSMState.OPENCONFIRM:
            if event_type == "BGPKeepaliveMessage":
                self._transition_to_established()
            elif event_type == "HoldTimerExpires" or event_type == "TcpConnectionFails":
                self._transition_to_idle()
            elif event_type == "BGPNotification":
                self._transition_to_idle()
        
        elif self.state == BGPFSMState.ESTABLISHED:
            if event_type == "BGPUpdateMessage":
                self._reset_hold_timer()
            elif event_type == "BGPKeepaliveMessage":
                self._reset_hold_timer()
            elif event_type == "HoldTimerExpires" or event_type == "TcpConnectionFails":
                self._transition_to_idle()
            elif event_type == "BGPNotification":
                self._transition_to_idle()

    # --- State Transition Methods ---
    def _transition_to_idle(self):
        if self.state != BGPFSMState.IDLE:
            self._stop_hold_timer()
            self._stop_connect_retry_timer()
            self._stop_open_delay_timer()
            self.state = BGPFSMState.IDLE
            print(f"Peer {self.peer_ip} transitioned to IDLE state.", flush=True)

    def _transition_to_connect(self):
        self.state = BGPFSMState.CONNECT
        print(f"Peer {self.peer_ip} transitioned to CONNECT state.", flush=True)
        self._start_connect_retry_timer()

    def _transition_to_active(self):
        self.state = BGPFSMState.ACTIVE
        print(f"Peer {self.peer_ip} transitioned to ACTIVE state.", flush=True)
        self._reset_connect_retry_timer()

    def _transition_to_opensent(self):
        self.state = BGPFSMState.OPENSENT
        print(f"Peer {self.peer_ip} transitioned to OPENSENT state.", flush=True)
        self._stop_connect_retry_timer()
        self._start_open_delay_timer()

    def _transition_to_confirm(self):
        self.state = BGPFSMState.OPENCONFIRM
        print(f"Peer {self.peer_ip} transitioned to OPENCONFIRM state.", flush=True)

    def _transition_to_established(self):
        self.state = BGPFSMState.ESTABLISHED
        print(f"Peer {self.peer_ip} transitioned to ESTABLISHED state.", flush=True)
        self._start_hold_timer()