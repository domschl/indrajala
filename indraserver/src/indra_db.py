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

    def _db_pragma(self, param, value):
        """ Execute a pragma command and verify result """
        set_cmd = f"PRAGMA {param} = {value};"
        self.cur.execute(set_cmd)
        self.conn.commit()
        get_cmd = f"PRAGMA {param};"
        self.cur.execute(get_cmd)
        result = self.cur.fetchone()
        if result and str(result[0]) == value:
            self.log.info(f"{set_cmd} OK")
            ret = True
        else:
            self.log.warning(f"{set_cmd} FAILED: {result}")
            ret = False
        return ret
        
    def _db_open(self):
        """ Open database and tune it using pragmas """
        self.conn = sqlite3.connect(self.database)
        self.cur = self.conn.cursor()
        opt = True

        # journalmode alternatives: DELETE, TRUNCATE, PERSIST, MEMORY, OFF
        if self._db_pragma("journal_mode", "wal") is False:
            opt = False
        
        #This line sets the page size of the memory to 4096 bytes. This is the size of a single page in the memory.
        # You can change this if you want to, but please be aware that the page size must be a power of 2.
        # For example, 1024, 2048, 4096, 8192, 16384, etc.
        if self._db_pragma("page_size", "4096") is False:
            opt = False

        # This is the number of pages that will be cached in memory. If you have a lot of memory, you can increase
        # this number to improve performance. If you have a small amount of memory, you can decrease this number to free up memory.
        if self._db_pragma("cache_size", "10000") is False:
            opt = False

        # This means that the database will be synced to disk after each transaction. If you don't want this, you can set it to off.
        # However, please be aware that this will make your database more vulnerable to corruption.
        # alternative: OFF=0, NORMAL=1, FULL=2, EXTRA
        if self._db_pragma("synchronous", "1") is False:   
            opt = False
        # alternative: DEFAULT=0, FILE=1, MEMORY=2
        if self._db_pragma("temp_store", "2") is False:
            opt = False
        if self._db_pragma("mmap_size", "1073741824") is False:  # 1G alternative: any positive integer
            opt = False

        if opt is False:
            self.log.warning("PRAGMA optimizations failures occured, this will affect performance.")
            
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
        return ret
    
    def outbound_init(self):
        db_dir = os.path.dirname(self.database)
        if os.path.exists(db_dir) is False:
            self.log.error(f"Database path {db_dir} does not exist!")
            return False
        ret = self._db_open()
        return True

    def shutdown(self):
        self.log.info("Closing database")
        self.conn.close()
    
    def outbound(self, ev:IndraEvent):
        self.log.info(f"Got a PingPong: {ev.domain}, sent by {ev.from_id}")
