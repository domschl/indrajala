import sqlite3
import time

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
        self.set_throttle(1)  # Max 1 message per sec to inbound
        self.database = os.path.expanduser(config_data["database"])

    def inbound_init(self):
        return True

    def inbound(self):
        time.sleep(1)
        return None

    def outbound_init(self):
        db_dir = os.path.dirname(self.database)
        if os.path.exists(db_dir) is False:
            self.log.error(f"Database path {db_dir} does not exist!")
            return False
        
        self.con = sqlite3.connect(self.database)
        self.cur = self.con.cursor()

        cmd = """
                         CREATE TABLE IF NOT EXISTS indra_events (
                        id INTEGER PRIMARY KEY,
                        seq_no INTEGER NOT NULL,
                        domain TEXT NOT NULL,
                        from_id TEXT NOT NULL,
                        uuid4 UUID NOT NULL,
                        parent_uuid4 UUID,
                        to_scope TEXT NOT NULL,
                        time_jd_start DOUBLE,
                        data_type TEXT NOT NULL,
                        data TEXT NOT NULL,
                        auth_hash TEXT,
                        time_jd_end DOUBLE
                    )
        """
        ret = self.cur.execute(cmd)
        self.log.info(f"Database opened: {ret}")
        return True

    def shutdown(self):
        self.log.info("Closing database")
        self.con.close()
    
    def outbound(self, ev:IndraEvent):
        self.log.info(f"Got a PingPong: {ev.domain}, sent by {ev.from_id}")
