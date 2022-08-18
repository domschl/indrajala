import asyncio
import os


class EventProcessor:
    def __init__(self, name, main_logger, toml_data):
        self.logger = main_logger
        self.toml_data = toml_data
        self.name = name
        self.active = False
        try:
            if self.toml_data[self.name]['active'] is False:
                return
            if os.path.isdir(self.toml_data[self.name]['rootpath']) is False:
                self.logger.error(f"{self.name}: Root directory {self.toml_data[self.name]['root']} does not exist")
                return
        except Exception as e:
            self.logger.error(f"{self.name}: {e}")
            return
        self.active = True

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
        msg = {'topic': 'hello', 'msg': 'world', 'origin': self.name}
        self.logger.debug(f"{self.name}: Sending message {msg}")
        # return {'topic': None, 'msg': None, 'origin': self.name}
        return msg

    async def put(self, msg):
        if self.active is False:
            return
        self.logger.debug(f"{self.name}: Received message {msg}")
        return
