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
        super().__init__(event_queue, send_queue, config_data, mode="single")
        self.sessions = {}
        self.subscribe(["$chat/#"])

    def outbound_init(self):
        self.log.info("Indra-dispatch init complete")
        return True

    def shutdown(self):
        self.log.info("Shutdown Dispatch complete")

    def outbound(self, ev: IndraEvent):
        self.log.info(f"Got something: {ev.domain}, sent by {ev.from_id}, ignored")
