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
            conn = psycopg.connect(self.toml_data[self.name]['connection'])
            conn.close()
            self.active = True
        except Exception as e:
            self.log.error(f"Connecting to database failed: {e}")
            self.active = False

    def isActive(self):
        return self.active
    
    async def async_init(self, loop):
        self.log.info("Async init start")
        if self.active is False:
            self.log.error("Async_init called even so database is not active!")
            return []
        self.loop = loop
        self.aconn = await psycopg.AsyncConnection.connect(self.toml_data[self.name]['connection'])
        self.log.info(f"aconn {self.aconn}")
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
        return
