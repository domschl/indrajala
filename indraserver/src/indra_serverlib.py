import multiprocessing as mp
import os
import json

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
    def __init__(self, loglevel, que, name):
        self.loglevels=['none', 'error', 'warning', 'info', 'debug']
        if loglevel in self.loglevels:
            self.loglevel = self.loglevels.index(loglevel)
        else:
            self.loglevel = self.loglevels.index('info')
        self.ev=IndraEvent()
        self.ev.data_type="string"
        self.ev.from_id=name;
        self.name=name
        self.que=que

    def _send_log(self, level, msg):
            self.ev.domain="$log/" + level
            self.ev.data=msg
            self.que.put(self.ev)
        
    def error(self, msg):
        if self.loglevel>0:
            self._send_log("error", msg);
    
    def warning(self, msg):
        if self.loglevel>1:
            self._send_log("warning", msg);
    
    def info(self, msg):
        if self.loglevel>2:
            self._send_log("info", msg);
    
    def debug(self, msg):
        if self.loglevel>3:
            self._send_log("debug", msg);

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
        if self.initialized is False:
            self.log.error("Indrajala unsubscribe(): connection data not initialized!")
            return False
        if self.websocket is None:
            self.log.error(
                "Websocket not initialized, please call init_connection() first!"
            )
            return False
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
