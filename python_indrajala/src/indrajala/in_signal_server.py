import sys
import signal
import atexit
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo


class EventProcessor:
    """ Check if another instance is already running using a socket server. Terminate old instance and
    start new instance (if kill option was not set.) """

    def __init__(self, name, main_logger, toml_data):
        self.log = logging.getLogger('indra.signal_server')  # main_logger
        self.port = int(toml_data[name]['signal_port'])
        self.toml_data = toml_data
        self.name = name

    async def async_init(self, loop):
        self.loop = loop
        self.exit_future = self.loop.create_future()
        await self.check_register_socket()
        return ["$SYS"]

    async def handle_client(self, reader, writer):
        request = ""
        while request != 'quit':
            request = (await reader.read(255)).decode('utf8').strip()
            self.log.debug(f"got socket [{request}]")
            if request == 'quit':
                response = 'quitting!\n'
            elif request == 'help':
                response = "help: this help\nquit: stop this daemon.\n"
            else:
                response = f'Error: {request} (try: help)\n'
            writer.write(response.encode('utf8'))
            await writer.drain()
        self.log.warning('quit received')
        writer.close()
        self.exit_future.set_result(True)
        self.exit = True

    async def get_command(self):
        ret = await self.exit_future
        return {'cmd': 'quit', 'retstate': ret}

    def close_daemon(self):
        pass

    def signal_handler(self, sig, frame):
        sys.exit(0)  # this will implicitly call atexit() handler close_daemon()

    async def check_register_socket(self):
        try:
            reader, writer = await asyncio.open_connection('localhost', self.port)
            message = 'quit\n'
            self.log.debug(f'Send: {message.strip()}')
            writer.write(message.encode())
            data = await reader.read(100)  # until('\n')
            writer.close()
            # await asyncio.sleep(1)  # otherwise new instance of keyboard fails

            self.log.debug(f'Received: {data.decode()!r}')
            if 'quitting' in data.decode():
                print('Other instance did terminate.')
                self.log.info("Old instance terminated.")
            if self.toml_data[self.name]['kill_daemon'] is True:
                print("Exiting after quitting other instance.")
                exit(0)
        except Exception as e:
            self.log.debug(f"Reading from socket failed: {e}")

        try:
            self.server = await asyncio.start_server(self.handle_client, 'localhost', self.port)
        except Exception as e:
            self.log.warning(f"Can't open server at port {self.port}: {e}")
            return None

        atexit.register(self.close_daemon)
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        return self.server

    async def get(self):
        _ = await self.exit_future
        return {'cmd': 'system', 'time': datetime.now(tz=ZoneInfo('UTC')), 'topic': '$SYS/PROCESS', 'msg': 'QUIT', 'origin': self.name}

    async def put(self, _):
        return
