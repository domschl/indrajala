import asyncio
import psycopg

class EventProcessor:
    def __init__(self, name, main_logger, toml_data):
        self.logger=main_logger
        self.toml_data=toml_data
        self.name=name
        try:
            self.conn = psycopg.connect(self.toml_data[self.name]['connection'])
            self.active = True
        except Exception as e:
            self.logger.error(f"Connecting to database failed: {e}")
            self.active=False
        return

    def isActive(self):
        return self.active

    async def async_init(self, loop):
        if self.active is False:
            return []
        self.loop=loop
        return ['#']

    async def get(self):
        if self.active is False:
            return None
        await asyncio.sleep(1.0)
        msg={'topic': 'hello', 'msg':'world', 'origin': self.name}
        self.logger.debug(f"{self.name}: Sending message {msg}")
        # return {'topic': None, 'msg': None, 'origin': self.name}
        return msg

    async def put(self, msg):
        if self.active is False:
            return
        self.logger.debug(f"{self.name}: Received message {msg}")
        return