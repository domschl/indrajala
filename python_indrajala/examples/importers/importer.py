import asyncio
# import ssl
import websockets


class IndrajalaImporter:
    def __init__(self, indrajala_host, ws_port, ssl=True, local_cert=None):
        self.indrajala_host = indrajala_host
        self.ws_port = ws_port
        self.ssl = ssl
        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        if self.ssl is True:
            if local_cert is not None:
                localhost_pem = local_cert
                self.ssl_context.load_verify_locations(localhost_pem)
            self.uri = f"wss://{self.indrajala_host}:{self.ws_port}"
        else:
            self.uri = f"ws://{self.indrajala_host}:{self.ws_port}"

    def import_dataframe(self, df, origin, domain, time_column_name, columms, column_name_transformers, column_transformers):
        
        msg = {}
        asyncio.run(self.send_msg(msg))
        pass

    async def send_msg(self, msg):
        async with websockets.connect(self.uri, ssl=self.ssl_context) as websocket:
            await websocket.send(msg)
            # greeting = await websocket.recv()
