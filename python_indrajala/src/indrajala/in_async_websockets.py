import os
import asyncio
import ssl
import websockets

class EventProcessor:
    def __init__(self, name, main_logger, toml_data):
        self.log=main_logger
        self.toml_data=toml_data
        self.name=name
        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.use_ssl=toml_data['in_async_websockets']['ssl']
        self.port=toml_data['in_async_websockets']['port']
        self.bind_address=toml_data['in_async_websockets']['bind_address']
        config_dir=toml_data['indrajala']['config_dir']
        cert_dir=os.path.join(config_dir,'certs')
        self.active=False
        self.enabled=False
        if self.use_ssl is True:
            cf=os.path.join(cert_dir,toml_data['in_async_websockets']['ssl_certfile'])
            kf=os.path.join(cert_dir,toml_data['in_async_websockets']['ssl_keyfile'])
            if os.path.exists(cf) is False:
                self.log.error(f"certfile {cf} does not exist!")
                return
            if os.path.exists(kf) is False:
                self.log.error(f"keyfile {kf} does not exist!")
                return
            try:
                self.ssl_context.load_cert_chain(certfile=cf, keyfile=kf)
                self.req_queue=asyncio.Queue()
                self.enabled = True
            except Exception as e:
                self.log.error(f"Failed to read ssl certs: {e}")
        return

    def isActive(self):
        return self.active

    async def server_task(self):
        self.log.info("Starting websockets server...")
        stop=asyncio.Future()
        await self.start_server
        self.log.info("Websockets server started.")
        self.online_future.set_result(0)
        self.active=True
        await stop
        self.log.info(f"Websockets: Terminated")

    async def async_init(self, loop):
        if self.enabled is False:
            return []
        self.loop=loop
        self.online_future=asyncio.Future()
        # async with websockets.serve(self.get_request, self.bind_address, self.port, ssl=self.ssl_context):
        #     await asyncio.Future();  # run forever
        self.start_server=websockets.serve(self.get_request, self.bind_address, self.port, ssl=self.ssl_context)
        return ['#']

    async def get_request(self, websocket, path):
        req = await websocket.recv()
        self.log.info(f"WS: {req}")
        self.req_queue.put_nowait(req)
        # await self.req_queue.put(req)
        # await websocket.send(greeting)

    async def get(self):
        if self.active is False:
            self.log.warning("WS-get before active!")
            await self.online_future
            self.log.info("WS got active, continuing!")
        self.log.info("Q-get")
        req=await self.req_queue.get()
        self.req_queue.task_done()
        self.log.info(f"WSTR: {req}")
        msg={'origin': self.name, 'topic': "ws", 'body':req}
        return msg

    async def put(self, msg):
        if self.active is False:
            return
        self.logger.debug(f"{self.name}: Received message {msg}")
        return
