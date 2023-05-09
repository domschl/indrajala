import asyncio
import ssl
from websockets.sync.client import connect


class IndrajalaImporter:
    def __init__(self, indrajala_host, ws_port, use_ssl=True, local_cert=None):
        self.indrajala_host = indrajala_host
        self.ws_port = ws_port
        self.use_ssl = use_ssl
        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        if self.use_ssl is True:
            if local_cert is not None:
                localhost_pem = local_cert
                self.ssl_context.load_verify_locations(localhost_pem)
            self.uri = f"wss://{self.indrajala_host}:{self.ws_port}"
        else:
            self.uri = f"ws://{self.indrajala_host}:{self.ws_port}"

    def import_dataframe(
        self,
        df,
        origin,
        domain,
        time_column_name,
        columms,
        column_name_transformers,
        column_transformers,
    ):
        msg = {}
        asyncio.run(self.send_msg(msg))
        pass

    async def send_msg(self, msg):
        async with websockets.connect("ws://localhost:8000") as websocket:
            await websocket.send("Hello, server!")
            response = await websocket.recv()
            print(f"Received message from server: {response}")


# asyncio.get_event_loop().run_until_complete(connect())
