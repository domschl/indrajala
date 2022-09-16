import asyncio
import psycopg
import signal
from datetime import datetime
from zoneinfo import ZoneInfo


class EventProcessor:
    def __init__(self, name, main_logger, toml_data):
        self.log = main_logger
        self.toml_data = toml_data
        try:
            self.disable_sync = toml_data[name]['disable_synchronous_commits']
        except Exception:
            self.log.error(f"disable_synchronous_commits not defined in {name}")
            self.disable_sync = False
        self.name = name
        self.table = 'prelim_events_v1'
        try:
            conn = psycopg.connect(self.toml_data[self.name]['connection'])
            conn.close()
            self.active = True
        except Exception as e:
            self.log.error(f"Connecting to database failed: {e}")
            self.active = False

    def isActive(self):
        return self.active

    async def async_init(self, loop):
        if self.active is False:
            self.log.error("Async_init called even so database is not active!")
            return []
        self.loop = loop
        self.aconn = await psycopg.AsyncConnection.connect(self.toml_data[self.name]['connection'])
        self.log.debug(f"aconn {self.aconn}")
        if self.disable_sync is True:
            await self.aconn.execute("SET synchronous_commit TO OFF")
        # Handle Ctrl-C:
        loop.add_signal_handler(signal.SIGINT, self.aconn.cancel)
        cmd = f"""
        CREATE TABLE {self.table} (
            timestamp double precision,
            uuid UUID,
            topic VARCHAR(256),
            msg VARCHAR(512),
            PRIMARY KEY (topic, timestamp)
        )
        """
        async with self.aconn.cursor() as acur:
            await acur.execute("select * from information_schema.tables where table_name=%s", (self.table,))
            rows = acur.rowcount
            if rows == 0:
                await acur.execute(cmd)
                await acur.execute("select * from information_schema.tables where table_name=%s", (self.table,))
                if acur.rowcount == 0:
                    self.log.error(f"Failed to create table {self.table}")
                    self.active = False
                    self.acur.close()
                else:
                    self.log.info(f"Database table {self.table} created.")
                    await acur.close()
                    await self.aconn.commit()
            else:
                self.log.info(f"Using existing database table {self.table}")
                await acur.close()
        return ['#']

    async def get(self):
        if self.active is False:
            return None
        await asyncio.sleep(60.0)
        msg = {'cmd': 'ping', 'topic': 'hello', 'msg': 'world', 'time': datetime.now(tz=ZoneInfo('UTC')), 'origin': self.name}
        self.log.debug(f"{self.name}: Sending message {msg}")
        # return {'topic': None, 'msg': None, 'origin': self.name}
        return msg

    async def put(self, msg):
        if self.active is False:
            return
        self.log.debug(f"{self.name}: Received message {msg}")
        async with self.aconn.cursor() as acur:
            tm = datetime.fromisoformat(msg['time']).timestamp()
            ins_cmd = f"INSERT INTO {self.table} (timestamp, uuid, topic, msg) VALUES (%s, %s, %s, %s)"
            await acur.execute(ins_cmd, (tm, msg['uuid'], msg['topic'], msg['msg']))
        await self.aconn.commit()
        self.log.debug(f"DB-write-commit {msg}")
        return
