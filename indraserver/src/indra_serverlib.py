import multiprocessing as mp
import os

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


class ProcLog:
    def __init__(self, loglevel, que, name):
        self.loglevels=['none', 'error', 'warning', 'info', 'debug']
        if loglevel in self.loglevels:
            self.loglevel = self.loglevels.index(loglevel)
        else:
            self.loglevel = self.loglevels.index('info')
        self.ev=IndraEvent()
        self.ev.data_type="string"
        self.ev.from_id=name;
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
