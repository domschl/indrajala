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

from indra_serverlib import IndraServerLib

class IndraProcess:
    def __init__(self, event_queue, send_queue, config_data):
        self.name = config_data['name']
        self.isl = IndraServerLib(self.name, event_queue, config_data["loglevel"])
        self.bActive = True
        self.send_queue = send_queue
        self.event_queue = event_queue
        self.config_data = config_data
        self.isl.info(f"IndraProcess {self.name} instantiated")

    def launcher(self):
        self.sender = threading.Thread(target = self.send_worker, name=self.name+"_send_worker", args=[])
        self.receiver = threading.Thread(target = self.receive_worker, name=self.name+"_receive_worker", args=[])
        self.sender.start()
        self.receiver.start()
        self.isl.info(f"Launcher of {self.name} started")
        while (self.bActive):
            time.sleep(0.1)
        self.isl.info(f"Launcher of {self.name} terminating...")

    def send_worker(self):
        self.isl.info(f"{self.name} started send_worker")
        for i in range(3):
            if self.bActive is False:
                return
            self.isl.info(f"Hello {i}!")
            time.sleep(1)
        # self.send_quit()
        while self.bActive is True:
            time.sleep(0.1)
        self.isl.info(f"{self.name} terminating send_worker")
        return
    
    def send_quit(self):
        ev = IndraEvent()
        ev.domain = "$sys/quit"
        self.event_queue.put(ev)

    def receive_worker(self):
        self.isl.info(f"{self.name} started receive_worker")
        while self.bActive is True:
            ev = self.send_queue.get()
            self.isl.info(f"Received: {ev.domain}")
            if ev.domain=="$sys/quit":
                self.isl.info(f"{self.name} terminating receive_worker")
                self.bActive=False
                self.sender.join(timeout=2)
                self.isl.info(f"Terminating process {self.name}")
                exit(0)
