import multiprocessing as mp
import os
import json
import threading
import time
import signal

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


class IndraServerLog:
    def __init__(self, name, event_queue, loglevel):
        self.loglevels=['none', 'error', 'warning', 'info', 'debug']
        if loglevel in self.loglevels:
            self.loglevel = self.loglevels.index(loglevel)
        else:
            self.loglevel = self.loglevels.index('info')
        self.name=name
        self.event_queue=event_queue

    def _send_log(self, level, msg):
        self.ev=IndraEvent()
        self.ev.data_type="string"
        self.ev.from_id=self.name
        self.ev.domain="$log/" + level
        self.ev.data=msg
        self.event_queue.put(self.ev)
        
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


    
class IndraProcessCore:
    def __init__(self, event_queue, send_queue, config_data, signal_handler=True):
        self.name = config_data['name']
        self.log = IndraServerLog(self.name, event_queue, config_data["loglevel"])
        self.bActive = True
        self.send_queue = send_queue
        self.event_queue = event_queue
        self.config_data = config_data
        self.throttle = 0

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        for sub in config_data['subscriptions']:
            self.subscribe(sub)
            
        self.log.info(f"IndraProcess {self.name} instantiated")

    def launcher(self):
        self.sender = threading.Thread(target = self.send_worker, name=self.name+"_send_worker", args=[])
        self.receiver = threading.Thread(target = self.receive_worker, name=self.name+"_receive_worker", args=[])
        self.sender.start()
        self.receiver.start()
        self.log.info(f"Launcher of {self.name} started")
        try:
            while (self.bActive):
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        self.log.info(f"Launcher of {self.name} terminating...")

    def is_active(self):
        """ Check if module is active """
        return self.bActive

    # def close_daemon(self):
    #     pass
    
    def signal_handler(self, sig, frame):
        sys.exit(0)

    def set_throttle(self, throttle):
        """ set a minimum pause between messages received from outside """
        self.throttle = throttle
            
    def send_worker(self):
        self.log.info(f"{self.name} started send_worker")
        if self.inbound_init() is True:
            while self.bActive is True:
                start = time.time()
                ev = self.inbound()
                if ev is not None:
                    self.event_queue.put(ev)
                    if self.throttle > 0:
                        if time.time()-start < self.throttle:
                            time.sleep(self.throttle)        
        self.log.info(f"{self.name} terminating send_worker")
        return

    def inbound_init(self):
        """ This function can optionally be overriden for init-purposes, needs to return True to start inbound() """
        return True
    
    def inbound(self):
        """ This function is overriden by the implementation: it acquires an object"""
        self.log.error(f"Process {self.name} doesn't override inbound function!")
        time.sleep(1)
        return None
        
    def receive_worker(self):
        self.log.info(f"{self.name} started receive_worker")
        if self.outbound_init() is True:
            while self.bActive is True:
                ev = self.send_queue.get()
                self.log.info(f"Received: {ev.domain}")
                if ev.domain=="$cmd/quit":
                    self.log.info(f"{self.name} terminating receive_worker")
                    self.bActive=False
                    self.sender.join(timeout=2)
                    self.log.info(f"Terminating process {self.name}")
                    exit(0)
                else:
                    self.outbound(ev)
        self.log.info(f"{self.name} receive_worker")
        return

    def outbound_init(self):
        """ This function can optionally be overriden for init-purposes, needs to return true to start output() """
        return True
    
    def outbound(self, ev: IndraEvent):
        """ THis function receives an IndraEvent object that is to be transmitted outbound """
        self.log.error(f"Process {self.name} doesn't override outbound function!")


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
        self.event_queue.put(ie)
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
        self.event_queue.put(ie)
        return True
