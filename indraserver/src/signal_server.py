import logging
import os
import time
import signal
import atexit
from datetime import datetime
from zoneinfo import ZoneInfo
import multiprocessing as mp

# XXX dev only
import sys

path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "indralib/src"
)
sys.path.append(path)
from indra_event import IndraEvent  # type: ignore

class ProcLog:
    def __init__(self, loglevel, que):
        self.loglevels=['none', 'error', 'warning', 'info', 'debug']
        if loglevel in self.loglevels:
            self.loglevel = self.loglevels.index(loglevel)
        else:
            self.loglevel = self.loglevels.index('info')
        self.ev=IndraEvent()
        self.que=que

    def error(self, msg):
        if self.loglevel>0:
            self.ev.domain="$sys/log/error"
            self.ev.data=msg
            self.ev.data_type="string"
            self.que.put(self.ev)
    
    def warning(self, msg):
        if self.loglevel>1:
            self.ev.domain="$sys/log/warning"
            self.ev.data=msg
            self.ev.data_type="string"
            self.que.put(self.ev)
    
    def info(self, msg):
        if self.loglevel>2:
            self.ev.domain="$sys/log/info"
            self.ev.data=msg
            self.ev.data_type="string"
            self.que.put(self.ev)
    
    def debug(self, msg):
        if self.loglevel>3:
            self.ev.domain="$sys/log/error"
            self.ev.data=msg
            self.ev.data_type="string"
            self.que.put(self.ev)
    
def indra_process(event_queue, send_queue, config_data):
    # print(config_data)
    log = ProcLog(config_data["loglevel"], event_queue)
    while True:
        time.sleep(1.0)
        log.info("Hello!")
        
