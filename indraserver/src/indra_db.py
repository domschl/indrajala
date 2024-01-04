import sqlite3

# XXX dev only
import sys
import os
path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "indralib/src"
)
sys.path.append(path)
from indra_event import IndraEvent  # type: ignore

from indra_serverlib import IndraProcessCore

class IndraProcess(IndraProcessCore):
    def __init__(self, event_queue, send_queue, config_data):
        super().__init__(event_queue, send_queue, config_data)
        self.n=0
        self.set_throttle(1)  # Max 1 message per sec to inbound
        self.database = config_data["database"]

    def inbound_init(self):
        return False

    def outbound_init(self):
        db_dir = os.path.dirname(self.database)
        if os.path.exists(db_dir) is False:
            self.log.error(f"Database path {db_dir} does not exist!")
            return False
        
        self.con = sqlite3.connect(self.database)
    
    def outbound(self, ev:IndraEvent):
        self.log.info(f"Got a PingPong: {ev.domain}, sent by {ev.from_id}")
