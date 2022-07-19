# import asyncio
import ssl
import websockets

class EventProcessor:
    def __init__(self, name, main_logger, toml_data):
        self.log=main_logger
        self.toml_data=toml_data
        self.name=name
        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.use_ssl=toml_data['in_async_websocket']['ssl']
        if self.use_ssl is True:
            try:
                self.ssl_context.load_cert_chain(certfile=toml_data['in_async_websocket']['ssl_certfile'], keyfile=toml_data['in_async_websocket']['ssl_keyfile'])
                self.active = True
            except Exception as e:
                self.log.error(f"Failed to read ssl certs: {e}")
                self.active = False
        return

    def isActive(self):
        return self.active

    async def async_init(self, loop):
        if self.active is False:
            return []
        self.loop=loop
        self.start_server = websockets.serve(self.get_request, 'localhost', 8765, ssl=ssl_context)
        self.loop.run_until_complete(self.start_server)
        return ['#']

    async def get_request(self, websocket, path):
        req = await websocket.recv()
        self.log.info(f"WS: {req}")
        # await websocket.send(greeting)

