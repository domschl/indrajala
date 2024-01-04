import multiprocessing as mp
import os
import json
import threading
import time

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 and older:
    import tomli as tomllib  # type: ignore

# XXX dev only
import sys
path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "indralib/src"
)
sys.path.append(path)
from indra_event import IndraEvent  # type: ignore


class IndraServerLib:
    def __init__(self, name, que, loglevel):
        self.loglevels=['none', 'error', 'warning', 'info', 'debug']
        if loglevel in self.loglevels:
            self.loglevel = self.loglevels.index(loglevel)
        else:
            self.loglevel = self.loglevels.index('info')
        self.name=name
        self.que=que

    def _send_log(self, level, msg):
        self.ev=IndraEvent()
        self.ev.data_type="string"
        self.ev.from_id=self.name
        self.ev.domain="$log/" + level
        self.ev.data=msg
        self.que.put(self.ev)
        
    def error(self, msg):
        if self.loglevel>0:
            self._send_log("error", msg)
    
    def warning(self, msg):
        if self.loglevel>1:
            self._send_log("warning", msg)
    
    def info(self, msg):
        if self.loglevel>2:
            self._send_log("info", msg)
    
    def debug(self, msg):
        if self.loglevel>3:
            self._send_log("debug", msg)

    def subscribe(self, domains):
        """Subscribe to domain"""
        if domains is None or domains == "":
            self.log.error("Please provide a valid domain(s)!")
            return False
        ie = IndraEvent()
        ie.domain = "$cmd/subs"
        ie.from_id = self.name
        ie.data_type = "vector/string"
        if isinstance(domains, list) is True:
            ie.data = json.dumps(domains)
        else:
            ie.data = json.dumps([domains])
        self.que.put(ie)
        return True

    def unsubscribe(self, domains):
        """Unsubscribe from domain"""
        if domains is None or domains == "":
            self.log.error("Please provide a valid domain(s)!")
            return False
        ie = IndraEvent()
        ie.domain = "$cmd/unsubs"
        ie.from_id = self.name
        ie.data_type = "vector/string"
        if isinstance(domains, list) is True:
            ie.data = json.dumps(domains)
        else:
            ie.data = json.dumps([domains])
        self.que.put(ie)
        return True

    
class IndraProcessCore:
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
        while self.bActive is True:
            start = time.time()
            self.inbound()
            if time.time()-start < 0.01:
                time.sleep(0.1)        
        self.isl.info(f"{self.name} terminating send_worker")
        return

    def inbound(self):
        ''' This function is overriden by the implementation: it acquires an object'''
        self.isl.error(f"Process {self.name} doesn't override inbound function!")
        time.sleep(1)
        return None
        
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
            else:
                self.outbound(ev)

    def outbound(self, ev: IndraEvent):
        ''' THis function receives an IndraEvent object that is to be transmitted outbound '''
        self.isl.error(f"Process {self.name} doesn't override outbound function!")

