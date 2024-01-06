# XXX dev only
import sys
import os

path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "indralib/src",
)
sys.path.append(path)
from indra_event import IndraEvent  # type: ignore

from indra_serverlib import IndraProcessCore


class IndraProcess(IndraProcessCore):
    def __init__(self, event_queue, send_queue, config_data):
        super().__init__(event_queue, send_queue, config_data)
        self.n = 0
        self.set_throttle(1.0/config_data['ping_frequency_hz'])  # Max 1 message per sec to inbound

    def inbound(self):
        self.n = self.n + 1
        self.log.debug(f"Padam! {self.n}")
        ev = IndraEvent()
        ev.from_id = self.name
        ev.domain = f"pingpong/{self.name}/{self.n}"
        return ev

    def outbound(self, ev: IndraEvent):
        self.log.debug(f"Got a PingPong: {ev.domain}, sent by {ev.from_id}")
