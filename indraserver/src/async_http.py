import asyncio
import ssl
import aiohttp
from aiohttp import web

# XXX dev only
import sys
import os
path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "indralib/src"
)
sys.path.append(path)
from indra_event import IndraEvent  # type: ignore

from indra_serverlib import IndraProcessCore

class IndraProcess(IndraProcessCore):
    def __init__(self, event_queue, send_queue, config_data):
        super().__init__(event_queue, send_queue, config_data, mode='async')

    async def async_init(self):
        self.port = self.config_data['port']
        self.bind_addresses = self.config_data['bind_addresses']
        self.web_root = os.path.expanduser(self.config_data['web_root'])
        self.private_key = None
        self.public_key = None
        self.ws_clients = []
        self.tls = False
        if self.config_data['tls'] is True:
            if os.path.exists(self.prefs['private_key']) is False:
                self.log.error(f"Private key file {self.config_data['private_key']} does not exist")
            elif os.path.exists(self.prefs['public_key']) is False:
                self.log.error(f"Public key file {self.config_data['public_key']} does not exist")
            else:
                self.private_key = self.config_data['private_key']
                self.public_key = self.config_data['public_key']
                self.tls = True
        self.app = web.Application(debug=True)
        self.app.add_routes([web.get('/', self.web_root_handler)])
        if self.tls is True:
            self.app.add_routes([web.get('/wss', self.websocket_handler)])
        else:
            self.app.add_routes([web.get('/ws', self.websocket_handler)])
        if self.tls is True:
            self.ssl_context = ssl.SSLContext()  # = TLS
            try:
                self.ssl_context.load_cert_chain(self.public_key, self.private_key)
            except Exception as e:
                self.log.error(f"Cannot create cert chain: {e}, not using TLS")
                self.tls = False
        asyncio.create_task(self.async_web_agent())

    async def async_web_agent(self):
        runner = web.AppRunner(self.app)
        await runner.setup()
        self.log.info("Starting web runner")
        if self.tls is True:
            self.log.info(f"TLS active, bind={self.bind_addresses}, port={self.port}")
            # print(f"Webclient at: https://localhost:{self.port}")
            site = web.TCPSite(runner, self.bind_addresses, self.port, ssl_context=self.ssl_context)
        else:
            self.log.info(f"TLS NOT active, bind={self.bind_addresses}, port={self.port}")
            site = web.TCPSite(runner, self.bind_addresses, self.port)            
            # print(f"Webclient at: http://localhost:{self.port}")
        await site.start()
        self.log.info("Web server active")
        while self.bActive:
            await asyncio.sleep(0.1)
        self.log.info("Web server stopped")
        
    def web_root_handler(self, request):
        return web.FileResponse(os.path.join(self.web_root, 'index.html'))

    async def websocket_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        if ws not in self.ws_clients:
            self.ws_clients.append(ws)
            self.log.info(f"New ws client {ws}! (clients: {len(self.ws_clients)})")
        else:
            self.thread_log.info(f"Client already registered! (clients: {len(self.ws_clients)})")

        try:
            await ws.send_str("hello")
        except Exception as e:
            self.log.warning("Sending to WebSocket client {} failed with {}".format(ws, e))
            return

        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                # if msg.data is not None:
                self.log.info("Client ws_dispatch: ws:{} msg:{}".format(ws, msg.data))
                try:
                    self.log.info(f"Received: {msg.data}")
                    # self.appque.put(json.loads(msg.data))
                except Exception as e:
                    self.log.warning(f"WebClient sent invalid JSON: {msg.data}: {e}")
            elif msg.type == aiohttp.WSMsgType.ERROR:
                self.log.warning(f'ws connection closed with exception {ws.exception()}')
                break
            else:
                self.log.error(f"Unexpected message {msg.data}, of type {msg.type}")
                break
        self.log.warning(f"WS-CLOSE: {ws}")
        self.ws_clients.remove(ws)

        return ws
    
    async def async_outbound(self, ev: IndraEvent):
        pass

    async def async_shutdown(self):
        pass
