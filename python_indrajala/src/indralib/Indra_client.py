import asyncio
import websockets
import logging
import ssl
import uuid
import toml


class IndraClient:
    def __init__(self, config_file="indra_client.toml"):
        self.log = logging.getLogger("IndraClient")
        self.initialized = self.get_config(config_file, verbose=False)
        
    def get_config(self, config_file, verbose=True):
        valid = True
        try:
            config = toml.load(config_file)
        except Exception as e:
            uri="ws://localhost:8083"
            if verbose is True:
                self.log.error(f{config_file} config file not found: {e}, using default {uri}")
            return False
        if 'uri' not in config:
            uri="ws://localhost:8083"
            if verbose is True:
                self.log.error(f"Please provide an uri=ws[s]://host:port in {config_file}, defaulting to {uri}")
        
   
    def init_connection(self, config)
        if use_ssl is True:
            ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            if "ca_authority" in config and config["ca_authority"] != "":
                ssl_ctx.load_verify_locations(cafile=config["ca_authority"])
        async with websockets.connect(url, ssl=ssl_ctx) as websocket:
            ie = IndraEvent(
                "$event/python/test",
                "ws/python",
                str(uuid.uuid4()),
                "to/test",
                IndraEvent.datetime2julian(datetime.datetime.utcnow()),
                "string/test",
                "3.1325",
                "hash",
                IndraEvent.datetime2julian(datetime.datetime.utcnow()),
            )
            await websocket.send(ie.to_json())

            while True:
                try:
                    message = await websocket.recv()
                    print(message)
                except Exception as e:
                    print(e)
                    break
    @staticmethod
    parse_url(url):
		
async def indra(config):
    """Connect to Indra server, use TLS"""
    url = config["url"]
    ssl_ctx = None
