import logging
import os
import time
import signal
import atexit
from datetime import datetime
from zoneinfo import ZoneInfo
import multiprocessing as mp
import threading

# XXX dev only
import sys

path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "indralib/src"
)
sys.path.append(path)
from indra_event import IndraEvent  # type: ignore

from indra_serverlib import IndraServerLib, IndraProcessCore

class IndraProcess(IndraProcessCore):
    def __init__(self, event_queue, send_queue, config_data):
        super().__init__(event_queue, send_queue, config_data)
        self.n=0

    def inbound(self):
        if self.n<3:
            self.n = self.n + 1
            self.isl.info(f"Padam! {self.n}")
            time.sleep(1)

    def outbound(self, ev:IndraEvent):
        self.isl.info(f"Don't know what to do with: {ev.domain}")
