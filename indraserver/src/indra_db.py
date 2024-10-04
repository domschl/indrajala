import sqlite3
import time
import json
import threading
import datetime
import uuid
import bcrypt
import os
import logging

from indralib.indra_event import IndraEvent  # type: ignore
from indralib.indra_time import IndraTime  # type: ignore
from indra_serverlib import IndraProcessCore


class IndraProcess(IndraProcessCore):
    def __init__(
        self,
        config_data,
        transport,
        event_queue,
        send_queue,
        zmq_event_queue_port,
        zmq_send_queue_port,
    ):
        super().__init__(
            config_data,
            transport,
            event_queue,
            send_queue,
            zmq_event_queue_port,
            zmq_send_queue_port,
            mode="single",
        )
        self.throttle = config_data["throttle"]
        if self.throttle is not None and self.throttle > 0:
            self.set_throttle(
                self.throttle
            )  # Max self.throttle message per sec to inbound  # XXX Why?
        self.database = os.path.expanduser(config_data["database"])
        self.database_directory = os.path.dirname(self.database)
        if os.path.exists(self.database_directory) is False:
            os.makedirs(self.database_directory)
            self.log.info(f"Created database directory {self.database_directory}")
        self.last_commit = 0
        self.commit_delay_sec = config_data["commit_delay_sec"]
        self.epsilon = config_data["epsilon"]
        if "page_size" in config_data:
            self.page_size = config_data["page_size"]
        else:
            self.page_size = 4096
        if "cache_size_pages" in config_data:
            self.cache_size_pages = config_data["cache_size_pages"]
        else:
            self.cache_size_pages = 10000
        self.bUncommitted = False
        self.commit_timer_thread = None
        self.sessions = {}
        self.subscribe(["$trx/db/#", "$trx/kv/#", "$event/#"])
        self._get_secure_key_names(config_data)
        self.unique_domains_cache = None

    def start_commit_timer(self):
        if self.commit_delay_sec > 0.0:
            self.commit_timer_thread = threading.Thread(
                target=self.commit_watchdog,
                name=self.name + "_commit_watchdog",
                args=[],
                daemon=True,
            )
            self.commit_timer_thread.start()

    def commit_watchdog(self):
        while self.bActive and self.commit_delay_sec > 0.0:
            time.sleep(self.commit_delay_sec)
            ev = IndraEvent()
            ev.domain = "$self/timer"
            self.event_send_self(ev)
        self.log.info("Timer thread terminated")

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
            self.last_state = {"last_seq_no": 0, "last_kv_seq_no": 0}
        if "last_seq_no" not in self.last_state:
            self.last_state["last_seq_no"] = 0
        if "last_kv_seq_no" not in self.last_state:
            self.last_state["last_kv_seq_no"] = 0

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

        cmd = "SELECT seq_no FROM indra_kv ORDER BY seq_no DESC LIMIT 1;"
        db_last_kv_seq = 0
        try:
            self.cur.execute(cmd)
            result = self.cur.fetchone()
            if result is not None:
                db_last_kv_seq = result[0]
            else:
                self.log.debug(
                    "No results when retrieving last kv seq_no, new database?"
                )
        except Exception as e:
            self.log.error("Failed to retrieve last kv seq_no from database")
        if db_last_kv_seq > self.last_state["last_kv_seq_no"]:
            self.last_state["last_kv_seq_no"] = db_last_kv_seq

        return (self.last_state["last_seq_no"], self.last_state["last_kv_seq_no"])

    def _write_last_seq_no(self):
        """Write a backup of the last used seq_no to json file"""
        seq_no, seq_kv_no = self._get_last_seq_no()
        last_state_file = os.path.join(self.database_directory, "last_state.json")
        with open(last_state_file, "w") as f:
            json.dump(self.last_state, f)
        return seq_no, seq_kv_no

    def _check_commit(self):
        if time.time() - self.last_commit > self.commit_delay_sec:
            self.conn.commit()
            self.bUncommitted = False
            self.log.debug("Commit due to timeout")
        else:
            if self.commit_timer_thread is None:
                self.start_commit_timer()
            self.bUncommitted = True
        self.last_commit = time.time()

    @staticmethod
    def hash_password(password):
        """
        Hashes a password using bcrypt.

        Args:
            password (str): The password to be hashed.

        Returns:
            str: The hashed password.

        Example:
            password = "my_secure_password"
            hashed_password = hash_password(password)
        """
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        return hashed_password.decode("utf-8")

    def check_password(self, plain_password: str, hashed_password: str):
        """
        Check if a plain password matches a hashed password.

        Args:
            plain_password (str): The plain password to be checked.
            hashed_password (str): The hashed password to compare against.

        Returns:
            bool: True if the plain password matches the hashed password, False otherwise.
        """
        try:
            checked = bcrypt.checkpw(
                plain_password.encode("utf-8"), hashed_password.encode("utf-8")
            )
        except Exception as e:
            self.log.error(f"Failed to check password: {e}")
            return False
        return checked

    def _create_session(self, key, from_id):
        user_template = "entity/indrajala/user/+/password"
        if IndraEvent.mqcmp(key, user_template) is False:
            return None
        user = key.split("/")[-2]
        # if user in self.sessions:
        #     return self.sessions[user]["session_id"]
        session_id = str(uuid.uuid4())
        self.log.info(f"Creating session {session_id} for {user}, {time.time()}")
        self.sessions[session_id] = {
            "user": user,
            "last_access": time.time(),
            "from_id": from_id,
        }
        ev = IndraEvent()
        ev.domain = f"$interactive/session/start/{user}"
        ev.from_id = self.name
        session_info = {
            "session_id": session_id,
            "user": user,
            "from_id": from_id,
        }
        ev.data_type = "session_info"
        ev.data = json.dumps(session_info)
        self.event_send(ev)
        self.log.info(f"Created session {session_id} for user {user}, {time.time()}")
        return session_id

    def _remove_session(self, session_id, from_id):
        if session_id in self.sessions:
            ev = IndraEvent()
            ev.domain = f"$interactive/session/end/{self.sessions[session_id]['user']}"
            ev.from_id = self.name
            session_info = {
                "session_id": session_id,
                "from_id": from_id,
            }
            ev.data_type = "session_info"
            ev.data = json.dumps(session_info)
            self.event_send(ev)
            self.log.info(
                f"Removed session {session_id} for user {self.sessions[session_id]['user']}"
            )
            del self.sessions[session_id]
            return True
        self.log.error(f"Session {session_id} not found")
        return False

    def _check_session(self, session_id):
        for session_id in self.sessions:
            self.sessions[session_id]["last_access"] = time.time()
            return self.session[session_id]
        return None

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
            self._check_commit()
            # self.log.info(f"Wrote {ev.uuid4}")
        except sqlite3.Error as e:
            self.log.error(f"Failed to write event-record: {e}")
            return False
        return True

    def _get_secure_key_names(self, config_data):
        self.secure_keys = ["entity/indrajala/user/+/password"]
        if "secure_keys" in config_data:
            self.secure_keys.append(config_data["secure_keys"])

    def _is_secure_key(self, key: str):
        """Check if a key is secure"""
        for secure_key in self.secure_keys:
            if IndraEvent.mqcmp(key, secure_key):
                return True
        return False

    def is_valid_key(self, key: str):
        key_parts = key.split("/")
        for key in key_parts:
            for c in key:
                if (
                    c
                    not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
                ):
                    return False
        return True

    def _write_update_kv(self, key: str, value: str):
        """Write a key/value pair. If the key already exists, update the value."""
        if self.is_valid_key(key) is False:
            self.log.error(f"Invalid key name {key}")
            return False
        self.last_state["last_kv_seq_no"] = self.last_state["last_kv_seq_no"] + 1
        if self._is_secure_key(key):
            value = self.hash_password(value)
        cmd = """INSERT OR REPLACE INTO indra_kv (
                    seq_no, key, value)
                 VALUES (
                    :seq_no, :key, :value);
              """
        try:
            self.cur.execute(
                cmd,
                {
                    "seq_no": self.last_state["last_kv_seq_no"],
                    "key": key,
                    "value": value,
                },
            )
            self._check_commit()
            # self.log.info(f"Wrote {key}")
        except sqlite3.Error as e:
            self.log.error(f"Failed to write kv-record: {e}")
            return False
        return True

    def _delete_event(self, uuid4: str):
        """Delete an IndraEvent from the database"""
        cmd = "DELETE FROM indra_events WHERE uuid4 = ?;"
        try:
            self.cur.execute(cmd, [uuid4])
            self._check_commit()
            # self.log.info(f"Deleted {uuid4}")
        except sqlite3.Error as e:
            self.log.error(f"Failed to delete event-record: {e}")
            return False
        return True

    def _delete_kv(self, key: str):
        """Delete a key/value pair from the database"""
        if "%" in key:
            op1 = "LIKE"
        else:
            op1 = "="
        cmd = f"DELETE FROM indra_kv WHERE key {op1} ?;"
        try:
            self.cur.execute(cmd, [key])
            self._check_commit()
            self.log.info(f"Deleted {key}")
        except sqlite3.Error as e:
            self.log.error(f"Failed to delete kv-record: {e}")
            return 0
        return self.cur.rowcount

    def _read_kv(self, key: str):
        """Read a value(s) from the database"""
        if "%" in key:
            op1 = "LIKE"
            lim = ""
        else:
            op1 = "="
            lim = " LIMIT 1"
        cmd = f"SELECT key, value FROM indra_kv WHERE key {op1} ?{lim};"
        start_time = time.time()
        try:
            self.cur.execute(cmd, [key])
            result = self.cur.fetchall()
            if result is not None:
                value = result
            else:
                value = None
        except sqlite3.Error as e:
            self.log.error(f"Failed to read kv-record: {e}")
            return None
        self.log.info(f"Read {key} in {time.time() - start_time:.4f} sec at {time.time()}")
        return value

    def _verify_kv(self, key: str, value: str):
        self.log.info(f"Verifying {key}, {time.time()}")
        if self._is_secure_key(key) is False:
            return False
        encr_pw = self._read_kv(key)
        if encr_pw is None or len(encr_pw) == 0 or len(encr_pw[0]) != 2:
            return False
        if self.check_password(value, encr_pw[0][1]) is True:
            self.log.info(f"Verified {key}, {time.time()}")
            return True
        return False

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
        if self._db_pragma("page_size", f"{self.page_size}") is False:
            opt = False

        # This is the number of pages that will be cached in memory. If you have a lot of memory, you can increase
        # this number to improve performance. If you have a small amount of memory, you can decrease this number to free up memory.
        if self._db_pragma("cache_size", f"{self.cache_size_pages}") is False:
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

        cmd = """CREATE TABLE IF NOT EXISTS indra_kv (
             id INTEGER PRIMARY KEY,
             seq_no INTEGER NOT NULL,
             key TEXT NOT NULL UNIQUE,
             value TEXT NOT NULL);
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

        cmd = """CREATE INDEX IF NOT EXISTS indra_kv_key ON indra_kv (key);
                 CREATE INDEX IF NOT EXISTS indra_kv_seq_no ON indra_kv (seq_no);
        """

        try:
            ret = self.cur.executescript(cmd)
        except sqlite3.Error as e:
            self.log.error(f"Failure to create indices: {e}")
            return False

        self.log.debug("Indices available")

        seq_no, seq_kv_no = self._get_last_seq_no()
        self.log.info(f"Database opened, seq_no={seq_no}, seq_kv_no={seq_kv_no}")
        return True

    def _db_seed_check(self):
        # create a default admin user, if kv is empty
        admin_user = "admin"
        admin_pw = "admin"
        admin_key_base = f"entity/indrajala/user/{admin_user}/"
        admin_key = admin_key_base + "password"
        def_props = [
            ("fullname", "Administrator"),
            ("email", "admin@localhost"),
            ("roles", '["admin"]'),
        ]
        def_test_users = [
            ("tati", "tati", "Tatjana Morgengrau", "tati@localhost", '["user"]'),
            ("frodo", "frodo", "Frodo", "frodo@localhost", '["user"]'),
            ("gandalf", "gandalf", "Gandalf the Grey", "gandi@localhost", '["admin"]'),
            ("importer", "importer", "Import Task", "import@localhost", '["app"]'),
            ("aragon", "aragon", "Aragon", "aragon@localhost", '["user"]'),
            (
                "legolas",
                "legolas",
                "Legolas Greenleaf",
                "legolas@localhost",
                '["user"]',
            ),
            ("backup", "backup", "Backup Task", "backup@localhost", '["app"]'),
            ("translator", "translator", "Translation AI", "ai@localhost", '["app"]'),
            ("stat", "stat", "Statistics", "stat@localhost", '["app", "user"]'),
            ("test10", "test10", "Test User 10", "test10@localhost", '["user"]'),
        ]
        cur_pwd = self._read_kv(admin_key)
        if cur_pwd is None or len(cur_pwd) == 0:
            self.log.info(f"Seeding database with default admin user {admin_user}")
            self._write_update_kv(
                admin_key, admin_pw
            )  # This will hash the password automatically
            for prop in def_props:
                self._write_update_kv(admin_key_base + prop[0], prop[1])
            # Seed test users   XXX to be removed
            for user in def_test_users:
                self.log.info(f"Seeding database with test user {user[0]}")
                self._write_update_kv(
                    f"entity/indrajala/user/{user[0]}/password", user[1]
                )
                self._write_update_kv(
                    f"entity/indrajala/user/{user[0]}/fullname", user[2]
                )
                self._write_update_kv(f"entity/indrajala/user/{user[0]}/email", user[3])
                self._write_update_kv(f"entity/indrajala/user/{user[0]}/roles", user[4])
        else:
            # Check if admin password is still default:
            if (
                len(cur_pwd) > 0
                and len(cur_pwd[0]) == 2
                and self.check_password(admin_pw, cur_pwd[0][1]) is True
            ):
                self.log.warning(
                    f"Admin user {admin_user} password is still set to default, please change it!"
                )
        return True

    def outbound_init(self):
        db_dir = os.path.dirname(self.database)
        if os.path.exists(db_dir) is False:
            self.log.error(f"Database path {db_dir} does not exist!")
            return False
        ret = self._db_open()
        if ret is False:
            return False
        ret = self._db_seed_check()
        return ret

    def shutdown(self):
        seq_no, seq_kv_no = self._write_last_seq_no()
        self.log.info(
            f"Closing database, last seq_no={seq_no}, last_kv_seq_no={seq_kv_no}"
        )
        self.conn.commit()
        self.conn.close()
        if self.commit_timer_thread is not None:
            self.commit_delay_sec = 0
            self.commit_timer_thread.join()
            self.log.info("Shutdown DB with commit-timer complete")
        else:
            self.log.info("Shutdown DB complete")

    def outbound(self, ev: IndraEvent):
        if ev.domain.startswith("$self/timer") is True:
            if self.bUncommitted is True:
                self.conn.commit()
                self.bUncommitted = False
                self.log.debug("Timer commit")
        elif ev.domain.startswith("$trx"):
            self.trx(ev)
        elif ev.domain.startswith("$event"):
            self._write_event(ev)
        else:
            self.log.info(f"Got something: {ev.domain}, sent by {ev.from_id}, ignored")

    def _trx_err(self, ev: IndraEvent, err_msg: str):
        self.log.error(err_msg)
        rev = IndraEvent()
        rev.domain = ev.from_id
        rev.from_id = self.name
        rev.uuid4 = ev.uuid4
        rev.to_scope = ev.domain
        rev.time_jd_start = IndraTime.datetime2julian(
            datetime.datetime.now(tz=datetime.timezone.utc)
        )
        rev.time_jd_end = IndraTime.datetime2julian(
            datetime.datetime.now(tz=datetime.timezone.utc)
        )
        rev.data_type = "error/invalid"
        rev.data = json.dumps(err_msg)
        self.event_send(rev)

    def trx(self, ev: IndraEvent):
        columns = [
            "id",
            "domain",
            "from_id",
            "uuid4",
            "parent_uuid4",
            "seq_no",
            "to_scope",
            "time_jd_start",
            "data_type",
            "data",
            "auth_hash",
            "time_jd_end",
        ]
        if ev.domain.startswith("$trx/db"):
            if ev.domain == "$trx/db/req/history":
                try:
                    rq_data = json.loads(ev.data)
                except Exception as e:
                    self._trx_err(
                        ev, f"Invalid $trx/db/req/history from {ev.from_id}: {ev.data}"
                    )
                    return

                rq_fields = [
                    "domain",
                    # "time_jd_start",
                    # "time_jd_end",
                    # "limit",
                    # "data_type",
                    "mode",
                ]
                valid = True
                inv_err = ""
                for field in rq_fields:
                    if field not in rq_data:
                        valid = False
                        inv_err = f"missing: {field}"
                        break
                if valid is False:
                    self._trx_err(
                        ev,
                        f"$trx/db/req/history from {ev.from_id} failed, request missing field {inv_err}",
                    )
                    return
                if rq_data["mode"] not in ["Sample", "Sequential"]:
                    self._trx_err(
                        ev,
                        f"$trx/db/req/history from {ev.from_id} failed, invalid mode {rq_data['mode']}",
                    )
                    return
                if "%" in rq_data["domain"]:
                    op1 = "LIKE"
                else:
                    op1 = "="
                sql_cmd = f"SELECT time_jd_start, data FROM (SELECT * FROM indra_events WHERE domain {op1} ?"  #  AND data_type {op2} ?)"
                q_params = [rq_data["domain"]]
                if (
                    "data_type" in rq_data
                    and rq_data["data_type"] is not None
                    and len(rq_data["data_type"]) > 0
                ):
                    if "%" in rq_data["data_type"]:
                        op2 = "LIKE"
                    else:
                        op2 = "="
                    q_params.append(rq_data["data_type"])
                    sql_cmd += f" AND data_type {op2} ?"
                if "time_jd_start" in rq_data and rq_data["time_jd_start"] is not None:
                    q_params.append(rq_data["time_jd_start"])
                    sql_cmd += " AND time_jd_start >= ?"
                if "time_jd_end" in rq_data and rq_data["time_jd_end"] is not None:
                    q_params.append(rq_data["time_jd_end"])
                    sql_cmd += " AND time_jd_end <= ?"
                if "limit" in rq_data and rq_data["limit"] is not None:
                    q_params.append(rq_data["limit"])
                    if rq_data["mode"] == "Sample":
                        sql_cmd += " ORDER BY RANDOM() LIMIT ?)"
                    elif rq_data["mode"] == "Sequential":
                        sql_cmd += " LIMIT ?)"
                    else:
                        self.log.error(
                            f"Failure, unexpected mode {rq_data['mode']}, internal error, rq from {ev.from_id}"
                        )
                else:
                    sql_cmd += ")"
                sql_cmd += " ORDER BY time_jd_start ASC;"
                t_start = datetime.datetime.now(tz=datetime.timezone.utc)
                self.log.info(f"Executing {sql_cmd} with {q_params}")
                self.cur.execute(sql_cmd, q_params)
                self.log.info(f"Executed {sql_cmd} with {q_params}")
                result = self.cur.fetchall()
                self.log.info(f"Result len: {len(result)}")
                rev = IndraEvent()
                rev.domain = ev.from_id
                rev.from_id = self.name
                rev.uuid4 = ev.uuid4
                rev.to_scope = ev.domain
                rev.time_jd_start = IndraTime.datetime2julian(t_start)
                rev.time_jd_end = IndraTime.datetime2julian(
                    datetime.datetime.now(tz=datetime.timezone.utc)
                )
                rev.data_type = "vector/tuple/jd/float"
                try:
                    jd_y = [(x[0], json.loads(x[1])) for x in result]
                    rev.data = json.dumps(jd_y)
                except Exception as e:
                    self.log.error(f"Failed to process result: {e}")
                    rev.data = json.dumps([])
                self.event_send(rev)
            elif ev.domain == "$trx/db/req/last":
                try:
                    rq_data = json.loads(ev.data)
                except Exception as e:
                    self._trx_err(
                        ev, f"Invalid $trx/db/req/last from {ev.from_id}: {ev.data}"
                    )
                    return
                rq_fields = [
                    "domain",
                ]
                valid = True
                inv_err = ""
                for field in rq_fields:
                    if field not in rq_data:
                        valid = False
                        inv_err = f"missing: {field}"
                        break
                if valid is False:
                    self._trx_err(
                        ev,
                        f"$trx/db/req/last from {ev.from_id} failed, request missing field {inv_err}",
                    )
                    return
                q_params = [rq_data["domain"]]
                sel_list = ", ".join(columns)
                sql_cmd = f"SELECT {sel_list} FROM indra_events WHERE domain = ? ORDER BY time_jd_start DESC LIMIT 1;"
                t_start = datetime.datetime.now(tz=datetime.timezone.utc)
                self.cur.execute(sql_cmd, q_params)
                result = self.cur.fetchall()
                rev = IndraEvent()
                rev.domain = ev.from_id
                rev.from_id = self.name
                rev.uuid4 = ev.uuid4
                rev.to_scope = ev.domain
                rev.time_jd_start = IndraTime.datetime2julian(t_start)
                rev.time_jd_end = IndraTime.datetime2julian(
                    datetime.datetime.now(tz=datetime.timezone.utc)
                )
                if result and len(result) == 1:
                    lev = IndraEvent.from_json(
                        json.dumps(dict(zip(columns, result[0])))
                    )
                    rev.data_type = "json/indraevent"
                    rev.data = lev.to_json()
                else:
                    self.log.warning(f"Not found: {sql_cmd} with {q_params}")
                    rev.data_type = "error/notfound"
                self.event_send(rev)
            elif ev.domain == "$trx/db/req/uniquedomains":
                try:
                    rq_data = json.loads(ev.data)
                except Exception as e:
                    self._trx_err(
                        ev,
                        f"Invalid $trx/db/req/uniquedomains from {ev.from_id}: {ev.data}",
                    )
                    return
                rq_fields = []
                valid = True
                inv_err = ""
                for field in rq_fields:
                    if field not in rq_data:
                        valid = False
                        inv_err = f"missing: {field}"
                        break
                if valid is False:
                    self._trx_err(
                        ev,
                        f"$trx/db/req/uniquedomains from {ev.from_id} failed, request missing field {inv_err}",
                    )
                    return
                q_params = []
                sql_cmd = f"SELECT DISTINCT domain FROM indra_events"
                post_filter = False
                if "data_type" in rq_data:
                    self.log.warning("Inefficient SQL query, uniqueDomain with data_type breaks optimization")
                    if "domain" in rq_data:
                        d = rq_data["domain"]
                        if "%" in d:
                            op1 = "LIKE"
                        else:
                            op1 = "="
                        q_params.append(d)
                        sql_cmd += f" WHERE domain {op1} ?"
                    dt = rq_data["data_type"]
                    if "%" in dt:
                        op2 = "LIKE"
                    else:
                        op2 = "="
                        q_params.append(dt)
                        sql_cmd += f" AND data_type {op2} ?"
                else:
                    post_filter = True
                sql_cmd += ";"
                if post_filter is True and self.unique_domains_cache is not None:
                    t_start = datetime.datetime.now(tz=datetime.timezone.utc)
                    self.log.info(f"Executing {sql_cmd} with {q_params}, using cache")
                    res_list = self.unique_domains_cache
                else:
                    t_start = datetime.datetime.now(tz=datetime.timezone.utc)
                    self.log.info(f"Executing {sql_cmd} with {q_params}")
                    self.cur.execute(sql_cmd, q_params)
                    result = self.cur.fetchall()
                    res_list = [x[0] for x in result]
                    self.unique_domains_cache = res_list
                if post_filter is True and "domain" in rq_data:
                    filter = rq_data["domain"].split("%")[0]
                    res_list = [x for x in res_list if x.startswith(filter)]
                rev = IndraEvent()
                rev.domain = ev.from_id
                rev.from_id = self.name
                rev.uuid4 = ev.uuid4
                rev.to_scope = ev.domain
                rev.time_jd_start = IndraTime.datetime2julian(t_start)
                rev.time_jd_end = IndraTime.datetime2julian(
                    datetime.datetime.now(tz=datetime.timezone.utc)
                )
                rev.data_type = "vector/string"
                rev.data = json.dumps(res_list)
                self.event_send(rev)
            elif ev.domain == "$trx/db/req/del":
                try:
                    rq_data = json.loads(ev.data)
                except Exception as e:
                    self._trx_err(
                        ev, f"Invalid $trx/db/req/del {ev.from_id}: {ev.data}"
                    )
                    return
                rq_fields = ["domains", "uuid4s"]
                valids = 0
                for field in rq_fields:
                    if field in rq_data:
                        valids += 1
                        break
                if valids != 1:
                    self._trx_err(
                        ev,
                        f"$trx/db/req/del from {ev.from_id} failed, requires either an array `uuid4s` or an array `domains` as key(s)",
                    )
                    return
                t_start = datetime.datetime.now(tz=datetime.timezone.utc)
                num_deleted = 0
                if "domains" in rq_data and rq_data["domains"] is not None:
                    if isinstance(rq_data["domains"], list):
                        # Handle array case
                        domains = rq_data["domains"]
                    else:
                        # Handle scalar case
                        domains = [rq_data["domains"]]
                    # Process the domains
                    for domain in domains:
                        if "%" in domain:
                            op1 = "LIKE"
                        else:
                            op1 = "="
                        sql_cmd = f"DELETE FROM indra_events WHERE domain {op1} ?"
                        q_params = [domain]
                        # check if data is deleted:
                        self.cur.execute(sql_cmd, q_params)
                        num_deleted += self.cur.rowcount
                    self._check_commit()
                elif "uuid4s" in rq_data and rq_data["uuid4s"] is not None:
                    if isinstance(rq_data["uuid4s"], list):
                        # Handle array case
                        uuid4s = rq_data["uuid4s"]
                    else:
                        # Handle scalar case
                        uuid4s = [rq_data["uuid4s"]]
                    # Process the uuid4s
                    for uuid4 in uuid4s:
                        sql_cmd = f"DELETE FROM indra_events WHERE uuid4 = ?"
                        q_params = [uuid4]
                        self.log.info(f"Deleting {uuid4} via {sql_cmd}")
                        self.cur.execute(sql_cmd, q_params)
                        num_deleted += self.cur.rowcount
                    self._check_commit()
                else:
                    self._trx_err(
                        ev,
                        f"$trx/db/req/del from {ev.from_id} failed, requires either an array `uuid4s` or an array `domains` as key(s)",
                    )
                    return
                if num_deleted > 0:
                    self.unique_domains_cache = None
                rev = IndraEvent()
                rev.domain = ev.from_id
                rev.from_id = self.name
                rev.uuid4 = ev.uuid4
                rev.to_scope = ev.domain
                rev.time_jd_start = IndraTime.datetime2julian(t_start)
                rev.time_jd_end = IndraTime.datetime2julian(
                    datetime.datetime.now(tz=datetime.timezone.utc)
                )
                rev.data_type = "number/int"
                rev.data = json.dumps(num_deleted)
                self.event_send(rev)
            elif ev.domain == "$trx/db/req/update":
                try:
                    rq_data = json.loads(ev.data)
                except Exception as e:
                    self._trx_err(
                        ev, f"Invalid $trx/db/req/update from {ev.from_id}: {ev.data}"
                    )
                    return
                # check if rq_data is an array, (if not, make it array of size 1) and that each element is a dict with the following:
                rq_fields = ["domain", "time_jd_start", "data_type", "data"]
                if not isinstance(rq_data, list):
                    rq_data = [rq_data]
                    self.log.warning(
                        f"Non-array input to $trx/db/req/update from {ev.from_id}, converted to array of size 1"
                    )
                valid = True
                inv_err = ""
                ut_start = IndraTime.datetime2julian(
                    datetime.datetime.now(tz=datetime.timezone.utc)
                )
                for rq in rq_data:
                    for field in rq_fields:
                        if field not in rq:
                            valid = False
                            inv_err = f"missing: {field} in {rq}"
                            break
                    if valid is False:
                        break
                if valid is False:
                    self._trx_err(
                        ev,
                        f"$trx/db/req/update from {ev.from_id} failed, request missing field {inv_err}",
                    )
                    return
                num_updated = 0
                for rq in rq_data:
                    # Search for `domain` and `time_jd_start` and update all fields in rq. If not
                    # found, insert a new record by creating a new IndraEvent() and then inserting all fields
                    # NO % wildcard

                    # Search for domain and time_jd_start:
                    fields = ", ".join(columns)
                    # If epsilon is > 0, searches for julian time allow variation of epsilon while still being considered equal.
                    # If epsilon is 0, searches for exact match of julian time.
                    # The trade-off is: epsilon=0 will lead to duplicate entries on update, since the float conversions
                    # between various languages and SQL are __not__ deterministic.
                    # epsilon > 0 will falsely equal entries that are not equal, but are within epsilon of each other.
                    if self.epsilon > 0:
                        sql_cmd = f"SELECT {fields} FROM indra_events WHERE domain = ? AND ABS(time_jd_start - ?) < {self.epsilon};"
                    else:
                        sql_cmd = f"SELECT {fields} FROM indra_events WHERE domain = ? AND time_jd_start = ?;"
                    q_params = [rq["domain"], rq["time_jd_start"]]
                    self.cur.execute(sql_cmd, q_params)
                    result = self.cur.fetchall()
                    # Check that exactly one record was found
                    if len(result) == 1:
                        changed = False
                        # Update the record
                        dev = dict(zip(columns, result[0]))
                        for key in rq:
                            if key in dev:
                                if (
                                    dev[key] != rq[key]
                                    and key != "seq_no"
                                    and key != "uuid4"
                                ):
                                    changed = True
                                    self.log.info(
                                        f"Updating {key} from {dev[key]} to {rq[key]} in {dev['uuid4']}"
                                    )
                                    dev[key] = rq[key]
                            else:
                                self.log.error(
                                    f"Invalid field {key} in $trx/db/req/update from {ev.from_id}, ignored"
                                )
                        if changed is True:
                            lev = IndraEvent.from_json(json.dumps(dev))
                            # Write the updated record
                            self.log.info(f"Updating {lev.uuid4}")
                            if self._delete_event(lev.uuid4) is True:
                                if self._write_event(lev) is True:
                                    num_updated += 1
                        else:
                            self.log.info(
                                f"No changes in {lev.uuid4}, not updated, rq from {ev.from_id}"
                            )
                    elif len(result) == 0:
                        # Insert a new record
                        dev = json.loads(IndraEvent().to_json())
                        for key in rq:
                            if key in dev:
                                dev[key] = rq[key]
                            else:
                                self.log.error(
                                    f"Invalid field {key} in $trx/db/req/update from {ev.from_id}, ignored"
                                )
                        lev = IndraEvent.from_json(json.dumps(dev))
                        if self._write_event(lev) is True:
                            num_updated += 1
                    else:
                        # More than one record found, this is an error
                        self.log.error(
                            f"Multiple records found for domain={rq['domain']} and time_jd_start={rq['time_jd_start']}, NOT UPDATED!"
                        )
                self._check_commit()
                self.unique_domains_cache = None
                rev = IndraEvent()
                rev.domain = ev.from_id
                rev.from_id = self.name
                rev.uuid4 = ev.uuid4
                rev.to_scope = ev.domain
                rev.time_jd_start = ut_start
                rev.time_jd_end = IndraTime.datetime2julian(
                    datetime.datetime.now(tz=datetime.timezone.utc)
                )
                rev.data_type = "number/int"
                rev.data = json.dumps(num_updated)
                self.event_send(rev)
            else:
                self._trx_err(ev, f"$trx/db not (yet!) implemented: {ev.domain}")
        elif ev.domain.startswith("$trx/kv"):
            # $trx/kv/req/write,read,delete
            if ev.domain == "$trx/kv/req/write":
                try:
                    rq_data = json.loads(ev.data)
                except Exception as e:
                    self._trx_err(
                        ev, f"Invalid $trx/kv/req/write from {ev.from_id}: {ev.data}"
                    )
                    return
                rq_fields = ["key", "value"]
                valid = True
                inv_err = ""
                for field in rq_fields:
                    if field not in rq_data:
                        valid = False
                        inv_err = f"missing: {field}"
                        break
                if valid is False:
                    self._trx_err(
                        ev,
                        f"$trx/kv/req/write from {ev.from_id} failed, request missing field {inv_err}",
                    )
                    return
                if self._write_update_kv(rq_data["key"], rq_data["value"]) is True:
                    rev = IndraEvent()
                    rev.domain = ev.from_id
                    rev.from_id = self.name
                    rev.uuid4 = ev.uuid4
                    rev.to_scope = ev.domain
                    rev.time_jd_start = IndraTime.datetime2julian(
                        datetime.datetime.now(tz=datetime.timezone.utc)
                    )
                    rev.time_jd_end = IndraTime.datetime2julian(
                        datetime.datetime.now(tz=datetime.timezone.utc)
                    )
                    rev.data_type = "string"
                    rev.data = json.dumps("OK")
                    self.event_send(rev)
                else:
                    self._trx_err(
                        ev,
                        f"$trx/kv/req/write from {ev.from_id} failed, internal error",
                    )
            elif ev.domain == "$trx/kv/req/read":
                try:
                    rq_data = json.loads(ev.data)
                except Exception as e:
                    self._trx_err(
                        ev, f"Invalid $trx/kv/req/read from {ev.from_id}: {ev.data}"
                    )
                    return
                print("KV-read!", rq_data)
                rq_fields = ["key"]
                valid = True
                inv_err = ""
                for field in rq_fields:
                    if field not in rq_data:
                        valid = False
                        inv_err = f"missing: {field}"
                        break
                if valid is False:
                    self._trx_err(
                        ev,
                        f"$trx/kv/req/read from {ev.from_id} failed, request missing field {inv_err}",
                    )
                    return
                values = self._read_kv(rq_data["key"])
                if values is not None:
                    rev = IndraEvent()
                    rev.domain = ev.from_id
                    rev.from_id = self.name
                    rev.uuid4 = ev.uuid4
                    rev.to_scope = ev.domain
                    rev.time_jd_start = IndraTime.datetime2julian(
                        datetime.datetime.now(tz=datetime.timezone.utc)
                    )
                    rev.time_jd_end = IndraTime.datetime2julian(
                        datetime.datetime.now(tz=datetime.timezone.utc)
                    )
                    rev.data_type = "vector/string"
                    rev.data = json.dumps(values)
                    self.event_send(rev)
                else:
                    self._trx_err(
                        ev,
                        f"$trx/kv/req/read from {ev.from_id} failed, not found",
                    )
            elif ev.domain == "$trx/kv/req/verify" or ev.domain == "$trx/kv/req/login":
                try:
                    rq_data = json.loads(ev.data)
                except Exception as e:
                    self._trx_err(
                        ev, f"Invalid $trx/kv/req/verify from {ev.from_id}: {ev.data}"
                    )
                    return
                rq_fields = ["key", "value"]
                valid = True
                inv_err = ""
                for field in rq_fields:
                    if field not in rq_data:
                        valid = False
                        inv_err = f"missing: {field}"
                        break
                if valid is False:
                    self._trx_err(
                        ev,
                        f"$trx/kv/req/verify from {ev.from_id} failed, request missing field {inv_err}",
                    )
                    return
                if self._verify_kv(rq_data["key"], rq_data["value"]) is True:
                    rev = IndraEvent()
                    rev.domain = ev.from_id
                    rev.from_id = self.name
                    rev.uuid4 = ev.uuid4
                    rev.to_scope = ev.domain
                    rev.time_jd_start = IndraTime.datetime2julian(
                        datetime.datetime.now(tz=datetime.timezone.utc)
                    )
                    rev.time_jd_end = IndraTime.datetime2julian(
                        datetime.datetime.now(tz=datetime.timezone.utc)
                    )
                    rev.data_type = "string"
                    rev.data = json.dumps("OK")
                    if ev.domain == "$trx/kv/req/login":
                        rev.auth_hash = self._create_session(
                            key=rq_data["key"], from_id=ev.from_id
                        )
                    self.event_send(rev)
                else:
                    self._trx_err(
                        ev,
                        f"$trx/kv/req/verify from {ev.from_id} failed, verify failed",
                    )
            elif ev.domain == "$trx/kv/req/logout":
                self.log.info(
                    f"Logout request from {ev.from_id}, session {ev.auth_hash}"
                )
                session_id = ev.auth_hash
                if self._remove_session(session_id, ev.from_id) is True:
                    rev = IndraEvent()
                    rev.domain = ev.from_id
                    rev.from_id = self.name
                    rev.uuid4 = ev.uuid4
                    rev.to_scope = ev.domain
                    rev.time_jd_start = IndraTime.datetime2julian(
                        datetime.datetime.now(tz=datetime.timezone.utc)
                    )
                    rev.time_jd_end = IndraTime.datetime2julian(
                        datetime.datetime.now(tz=datetime.timezone.utc)
                    )
                    rev.data_type = "string"
                    rev.data = json.dumps("OK")
                    self.log.info(f"Logged out session {session_id}")
                    self.event_send(rev)
                else:
                    self._trx_err(
                        ev,
                        f"$trx/kv/req/logout from {ev.from_id} failed, session {session_id} unknown",
                    )

            elif ev.domain == "$trx/kv/req/delete":
                try:
                    rq_data = json.loads(ev.data)
                except Exception as e:
                    self._trx_err(
                        ev, f"Invalid $trx/kv/req/delete from {ev.from_id}: {ev.data}"
                    )
                    return
                rq_fields = ["key"]
                valid = True
                inv_err = ""
                for field in rq_fields:
                    if field not in rq_data:
                        valid = False
                        inv_err = f"missing: {field}"
                        break
                if valid is False:
                    self._trx_err(
                        ev,
                        f"$trx/kv/req/delete from {ev.from_id} failed, request missing field {inv_err}",
                    )
                    return
                cnt = self._delete_kv(rq_data["key"])
                if cnt > 0:
                    rev = IndraEvent()
                    rev.domain = ev.from_id
                    rev.from_id = self.name
                    rev.uuid4 = ev.uuid4
                    rev.to_scope = ev.domain
                    rev.time_jd_start = IndraTime.datetime2julian(
                        datetime.datetime.now(tz=datetime.timezone.utc)
                    )
                    rev.time_jd_end = IndraTime.datetime2julian(
                        datetime.datetime.now(tz=datetime.timezone.utc)
                    )
                    rev.data_type = "string"
                    rev.data = json.dumps(f"OK, {cnt} deleted")
                    self.event_send(rev)
                else:
                    self._trx_err(
                        ev,
                        f"$trx/kv/req/delete from {ev.from_id} failed, not found",
                    )
        else:
            self.log.error(f"Not implemented: {ev.domain}, invalid request")

        # entity, location, event, session

        # $trx/entity/user/login/userid
        # $trx/entity/user/create/userid
        # $trx/entity/user/delete/userid
        # $trx/entity/user/rename/userid
        # $trx/entity/user/read/userid

        # $trx/location/read/location-id
        # $trx/location/create/location-id
        # $trx/location/delete/location-id
        # $trx/location/read/location-id

        # $trx/session/read/session-id
