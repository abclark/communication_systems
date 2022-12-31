from dataclasses import dataclass


@dataclass
class CongestionDecision:
    cwnd: int
    pacing_interval: float
    state: str
    avg_rtt: float = 0.0
    rtprop: float = 0.0
    rtprop_reset: bool = False


class CongestionController:
    def on_ack(self, rtt: float):
        raise NotImplementedError

    def update(self, now: float) -> CongestionDecision:
        raise NotImplementedError


class BBR(CongestionController):
    RTT_THRESHOLD = 1.25
    DRAIN_EXIT = 1.10
    CRUISE_DURATION = 5.0
    PROBE_RTT_INTERVAL = 10.0
    PROBE_RTT_DURATION = 0.2
    PROBE_RTT_CWND = 4
    DRAIN_TIMEOUT = 5.0
    UPDATE_INTERVAL = 0.5
    MIN_SAMPLES = 20

    def __init__(self):
        self.rtt_samples = []
        self.rtprop = None
        self.rtprop_updated_time = 0
        self.cwnd = 1
        self.state = 'STARTUP'
        self.state_start_time = 0
        self.last_update = 0
        self.pre_probe_rtt_cwnd = None

    def on_ack(self, rtt: float):
        self.rtt_samples.append(rtt)

    def update(self, now: float) -> CongestionDecision:
        self._rtprop_reset = False

        if len(self.rtt_samples) >= self.MIN_SAMPLES:
            if now - self.last_update >= self.UPDATE_INTERVAL:
                self._run_state_machine(now)
                self.last_update = now

        pacing = self.rtprop / self.cwnd if self.rtprop and self.cwnd > 0 else 0
        avg_rtt = sum(self.rtt_samples[-50:]) / len(self.rtt_samples[-50:]) if self.rtt_samples else 0

        return CongestionDecision(
            cwnd=self.cwnd,
            pacing_interval=pacing,
            state=self.state,
            avg_rtt=avg_rtt,
            rtprop=self.rtprop or 0,
            rtprop_reset=self._rtprop_reset
        )

    def _run_state_machine(self, now: float):
        recent = self.rtt_samples[-50:]
        avg_rtt = sum(recent) / len(recent)
        min_rtt = min(recent)

        if self.rtprop is None or min_rtt < self.rtprop:
            self.rtprop = min_rtt
            self.rtprop_updated_time = now

        ratio = avg_rtt / self.rtprop

        if self.state == 'STARTUP':
            if ratio < self.RTT_THRESHOLD:
                self.cwnd = self.cwnd + 1 if self.cwnd < 10 else int(self.cwnd * 1.25)
            else:
                self.state = 'DRAIN'
                self.state_start_time = now

        elif self.state == 'CRUISE':
            if now - self.rtprop_updated_time > self.PROBE_RTT_INTERVAL:
                self.pre_probe_rtt_cwnd = self.cwnd
                self.cwnd = self.PROBE_RTT_CWND
                self.state = 'PROBE_RTT'
                self.state_start_time = now
            elif now - self.state_start_time > self.CRUISE_DURATION:
                self.state = 'PROBE'
                self.state_start_time = now

        elif self.state == 'PROBE':
            if ratio < self.RTT_THRESHOLD:
                self.cwnd = self.cwnd + 1 if self.cwnd < 10 else int(self.cwnd * 1.25)
            else:
                self.state = 'DRAIN'
                self.state_start_time = now

        elif self.state == 'DRAIN':
            if ratio < self.DRAIN_EXIT:
                self.state = 'CRUISE'
                self.state_start_time = now
            elif now - self.state_start_time > self.DRAIN_TIMEOUT:
                self.rtprop = min_rtt
                self.rtprop_updated_time = now
                self._rtprop_reset = True
            else:
                self.cwnd = max(1, self.cwnd - 1)

        elif self.state == 'PROBE_RTT':
            if now - self.state_start_time > self.PROBE_RTT_DURATION:
                self.cwnd = self.pre_probe_rtt_cwnd
                self.rtprop_updated_time = now
                self.state = 'CRUISE'
                self.state_start_time = now
