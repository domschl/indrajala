import sqlite3
import time
import json

# XXX dev only
import sys
import os

path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "indralib/src",
)
sys.path.append(path)
from indra_event import IndraEvent  # type: ignore

from indra_serverlib import IndraProcessCore


class IndraProcess(IndraProcessCore):
    def __init__(self, event_queue, send_queue, config_data):
        super().__init__(event_queue, send_queue, config_data, mode="single")
        self.set_throttle(1)  # Max 1 message per sec to inbound
        self.database = os.path.expanduser(config_data["database"])
        self.database_directory = os.path.dirname(self.database)

    # def inbound_init(self):
    #     return True

    # def inbound(self):
    #     time.sleep(1)
    #     return None

    def _db_pragma(self, param, value):
        """Execute a pragma command and verify result"""
        set_cmd = f"PRAGMA {param} = {value};"
        self.cur.execute(set_cmd)
        self.conn.commit()
        get_cmd = f"PRAGMA {param};"
        self.cur.execute(get_cmd)
        result = self.cur.fetchone()
        if result and str(result[0]) == value:
            self.log.debug(f"{set_cmd} OK")
            ret = True
        else:
            self.log.warning(f"{set_cmd} FAILED: {result}")
            ret = False
        return ret

    def _get_last_seq_no(self):
        """Get highest seq_no from either json-backup or database"""
        last_state_file = os.path.join(self.database_directory, "last_state.json")
        self.last_state = None
        if os.path.exists(last_state_file):
            with open(last_state_file, "r") as f:
                self.last_state = json.load(f)
        if self.last_state is None:
            self.last_state = {"last_seq_no": 0}
        cmd = "SELECT seq_no FROM indra_events ORDER BY seq_no DESC LIMIT 1;"
        db_last_seq = 0
        try:
            self.cur.execute(cmd)
            result = self.cur.fetchone()
            if result is not None:
                db_last_seq = result[0]
            else:
                self.log.debug("No results when retrieving last seq_no, new database?")
        except Exception as e:
            self.log.error("Failed to retrieve last seq_no from database")
        if db_last_seq > self.last_state["last_seq_no"]:
            self.last_state["last_seq_no"] = db_last_seq
        return self.last_state["last_seq_no"]

    def _write_last_seq_no(self):
        """Write a backup of the last used seq_no to json file"""
        seq_no = self._get_last_seq_no()
        last_state_file = os.path.join(self.database_directory, "last_state.json")
        with open(last_state_file, "w") as f:
            json.dump(self.last_state, f)
        return seq_no

    def _write_event(self, ev: IndraEvent):
        """Write an IndraEvent to the database"""
        self.last_state["last_seq_no"] = self.last_state["last_seq_no"] + 1
        ev.seq_no = self.last_state["last_seq_no"]
        cmd = """INSERT INTO indra_events (
                    domain, from_id, uuid4, parent_uuid4,
                    seq_no, to_scope, time_jd_start, data_type,
                    data, auth_hash, time_jd_end)
                 VALUES (
                    :domain, :from_id, :uuid4, :parent_uuid4,
                    :seq_no, :to_scope, :time_jd_start, :data_type,
                    :data, :auth_hash, :time_jd_end);
              """
        try:
            self.cur.execute(cmd, vars(ev))
        except sqlite3.Error as e:
            self.log.error(f"Failed to write event-record: {e}")
            return False
        return True

    def _db_open(self):
        """Open database and tune it using pragmas"""
        try:
            self.conn = sqlite3.connect(self.database)
            self.cur = self.conn.cursor()
        except sqlite3.Error as e:
            self.log.error(f"Failed to open database at {self.database}: {e}")
            return False

        opt = True

        # journalmode alternatives: DELETE, TRUNCATE, PERSIST, MEMORY, OFF
        if self._db_pragma("journal_mode", "wal") is False:
            opt = False

        # This line sets the page size of the memory to 4096 bytes. This is the size of a single page in the memory.
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
        if (
            self._db_pragma("mmap_size", "1073741824") is False
        ):  # 1G alternative: any positive integer
            opt = False

        if opt is False:
            self.log.warning(
                "PRAGMA optimizations failures occured, this will affect performance."
            )
        else:
            self.log.debug("PRAGMA optimization success")

        cmd = """CREATE TABLE IF NOT EXISTS indra_events (
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
                 time_jd_end DOUBLE );
              """
        try:
            ret = self.cur.execute(cmd)
        except sqlite3.Error as e:
            self.log.error(f"Failure to create table: {e}")
            return False

        self.log.debug("Tables available")

        cmd = """CREATE INDEX IF NOT EXISTS indra_events_domain ON indra_events (domain);
                 CREATE INDEX IF NOT EXISTS indra_events_from_id ON indra_events (to_scope);
                 CREATE INDEX IF NOT EXISTS indra_events_time_start ON indra_events (time_jd_start);
                 CREATE INDEX IF NOT EXISTS indra_events_data_type ON indra_events (data_type);
                 CREATE INDEX IF NOT EXISTS indra_events_time_end ON indra_events (time_jd_end);
                 CREATE INDEX IF NOT EXISTS indra_events_seq_no ON indra_events (seq_no);
                 CREATE INDEX IF NOT EXISTS indra_events_uuid4 ON indra_events (uuid4);
                 CREATE INDEX IF NOT EXISTS indra_events_parent_uuid4 ON indra_events (parent_uuid4);
              """
        try:
            ret = self.cur.executescript(cmd)
        except sqlite3.Error as e:
            self.log.error(f"Failure to create indices: {e}")
            return False

        self.log.debug("Indices available")

        seq_no = self._get_last_seq_no()
        self.log.info(f"Database opened, seq_no={seq_no}")
        return True

    def outbound_init(self):
        db_dir = os.path.dirname(self.database)
        if os.path.exists(db_dir) is False:
            self.log.error(f"Database path {db_dir} does not exist!")
            return False
        ret = self._db_open()
        return ret

    def shutdown(self):
        seq_no = self._write_last_seq_no()
        self.log.info(f"Closing database, last seq_no={seq_no}")
        self.conn.close()

    def outbound(self, ev: IndraEvent):
        if ev.domain.startswith("$trx"):
            self.log.warning(f"$trx request not yet implemented: {ev.domain}")
        elif ev.domain.startswith("mqtt"):
            self._write_event(ev)
        else:
            self.log.info(f"Got something: {ev.domain}, sent by {ev.from_id}, ignored")
