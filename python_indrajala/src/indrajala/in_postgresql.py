import asyncio

class EventProcessor:
    def __init__(self, name, main_logger, toml_data):
        self.logger=main_logger
        self.toml_data=toml_data
        self.name=name
        return

    async def async_init(self, loop):
        self.loop=loop
        return ['#']

    async def get(self):
        await asyncio.sleep(1.0)
        msg={'topic': 'hello', 'msg':'world', 'origin': self.name}
        self.logger.debug(f"{self.name}: Sending message {msg}")
        return msg

    async def put(self, msg):
        self.logger.debug(f"{self.name}: Received message {msg}")
        return
