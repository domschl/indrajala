import asyncio
import psycopg
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

class EventProcessor:
    def __init__(self, name, main_logger, toml_data):
        self.log = main_logger
        self.toml_data = toml_data
        self.name = name
        self.table = 'prelim_events_v1'
        try:
            self.conn = psycopg.connect(self.toml_data[self.name]['connection'])
            self.active = True
        except Exception as e:
            self.log.error(f"Connecting to database failed: {e}")
            self.active = False
        if self.active is True:
            cur=self.conn.cursor()
            cur.execute("select * from information_schema.tables where table_name=%s", (self.table,))
            if cur.rowcount > 0:
                self.log.info(f"Connected to database table {self.table}")
            else:
                cmd = f"""
                CREATE TABLE {self.table} (
                    timestamp double precision,
                    uuid UUID,
                    topic VARCHAR(256),
                    msg VARCHAR(512),
                    PRIMARY KEY (topic, timestamp)
                )
                """
                self.log.info(f"executing create table {cmd}")
                cur.execute(cmd)
                cur.execute("select * from information_schema.tables where table_name=%s", (self.table,))
                if cur.rowcount == 0:
                    self.log.error(f"Creating the table went wrong!")
                else:
                    self.log.info(f"Created new database table {self.table}")
            cur.close()
            self.conn.commit()


        return

    def isActive(self):
        return self.active

    async def async_init(self, loop):
        if self.active is False:
            return []
        self.loop = loop
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
        return
