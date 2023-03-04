from enum import Enum
import threading

class BGPFSMState(Enum):
    IDLE = 0
    CONNECT = 1
    ACTIVE = 2
    OPENSENT = 3
    OPENCONFIRM = 4
    ESTABLISHED = 5

class BGPPeer:
    def __init__(self, peer_ip, verbose_timers=False):
        self.peer_ip = peer_ip
        self.state = BGPFSMState.IDLE
        self.verbose_timers = verbose_timers

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

    def _log_timer(self, msg):
        """Only print timer messages if verbose_timers is True."""
        if self.verbose_timers:
            print(f"  [{self.peer_ip}] {msg}", flush=True)

    def _log_transition(self, from_state, to_state, reason=""):
        """Print a visual state transition."""
        reason_str = f" ({reason})" if reason else ""
        print(f"  {self.peer_ip}: {from_state.name} ──▶ {to_state.name}{reason_str}", flush=True)

    # --- Timer Management ---
    def _start_hold_timer(self):
        if self.hold_timer_running:
            self._stop_hold_timer()
        self.hold_timer = threading.Timer(self.hold_time, self.handle_event, ["HoldTimerExpires"])
        self.hold_timer.start()
        self.hold_timer_running = True
        self._log_timer(f"Hold Timer started ({self.hold_time}s)")

    def _stop_hold_timer(self):
        if self.hold_timer_running:
            self.hold_timer.cancel()
            self.hold_timer_running = False
            self._log_timer("Hold Timer stopped")

    def _reset_hold_timer(self):
        self._start_hold_timer()
        self._log_timer("Hold Timer reset")

    def _start_connect_retry_timer(self):
        if self.connect_retry_timer_running:
            self._stop_connect_retry_timer()
        self.connect_retry_timer = threading.Timer(self.connect_retry_time, self.handle_event, ["ConnectRetryTimerExpires"])
        self.connect_retry_timer.start()
        self.connect_retry_timer_running = True
        self._log_timer(f"Connect Retry Timer started ({self.connect_retry_time}s)")

    def _stop_connect_retry_timer(self):
        if self.connect_retry_timer_running:
            self.connect_retry_timer.cancel()
            self.connect_retry_timer_running = False
            self._log_timer("Connect Retry Timer stopped")

    def _reset_connect_retry_timer(self):
        self._start_connect_retry_timer()
        self._log_timer("Connect Retry Timer reset")

    def _start_open_delay_timer(self):
        if self.open_delay_timer_running:
            self._stop_open_delay_timer()
        self.open_delay_timer = threading.Timer(self.open_delay_time, self.handle_event, ["OpenDelayTimerExpires"])
        self.open_delay_timer.start()
        self.open_delay_timer_running = True
        self._log_timer(f"Open Delay Timer started ({self.open_delay_time}s)")

    def _stop_open_delay_timer(self):
        if self.open_delay_timer_running:
            self.open_delay_timer.cancel()
            self.open_delay_timer_running = False
            self._log_timer("Open Delay Timer stopped")

    # --- FSM Event Handler ---
    def handle_event(self, event_type, *args, **kwargs):
        old_state = self.state

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
            old_state = self.state
            self._stop_hold_timer()
            self._stop_connect_retry_timer()
            self._stop_open_delay_timer()
            self.state = BGPFSMState.IDLE
            self._log_transition(old_state, self.state)

    def _transition_to_connect(self):
        old_state = self.state
        self.state = BGPFSMState.CONNECT
        self._log_transition(old_state, self.state)
        self._start_connect_retry_timer()

    def _transition_to_active(self):
        old_state = self.state
        self.state = BGPFSMState.ACTIVE
        self._log_transition(old_state, self.state)
        self._reset_connect_retry_timer()

    def _transition_to_opensent(self):
        old_state = self.state
        self.state = BGPFSMState.OPENSENT
        self._log_transition(old_state, self.state)
        self._stop_connect_retry_timer()
        self._start_open_delay_timer()

    def _transition_to_confirm(self):
        old_state = self.state
        self.state = BGPFSMState.OPENCONFIRM
        self._log_transition(old_state, self.state)

    def _transition_to_established(self):
        old_state = self.state
        self.state = BGPFSMState.ESTABLISHED
        self._log_transition(old_state, self.state, "Session up!")
        self._start_hold_timer()
