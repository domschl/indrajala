import asyncio
import websockets
import logging
import ssl
import uuid
import toml
import datetime

from indra_event import IndraEvent

class IndraClient:
    def __init__(self, uri=None, ca_authority=None, auth_token=None, config_file="indra_client.toml"):
        self.log = logging.getLogger("IndraClient")
        if config_file is not None and config_file != "":
            self.initialized = self.get_config(config_file, verbose=False)
        elif uri is not None and uri != "":
            self.initialized = True
            self.uri = uri
            if ca_authority is not None and ca_authority!="":
                self.ca_authority = ca_authority
            else:
                self.ca_authority = None
            if auth_token is not None and auth_token!="":
                self.auth_token = auth_token
            else:
                self.auth_token = None
            if self.uri.startswith("wss://"):
                self.use_ssl = True
            else:
                self.use_ssl = False
    
    def get_config(self, config_file, verbose=True):
        """Get config from file"""
        self.initialized = False
        try:
            config = toml.load(config_file)
        except Exception as e:
            if verbose is True:
                self.log.error(f"{config_file} config file not found: {e}")
            return False
        if 'uri' not in config:
            if verbose is True:
                self.log.error(f"Please provide an uri=ws[s]://host:port in {config_file}")
            return False
        self.uri = config["uri"]
        if "ca_authority" in config and config["ca_authority"] != "":
            self.ca_authority = config["ca_authority"]
        else:
            self.ca_authority = None
        if "auth_token" in config and config["auth_token"] != "":
            self.auth_token = config["auth_token"]
        else:
            self.auth_token = None
        if self.uri.startswith("wss://"):
            self.use_ssl = True
        else:
            self.use_ssl = False
        self.initialized = True
        return True

   
    async def init_connection(self, verbose=False):
        """Initialize connection"""
        if self.initialized is False:
            if verbose is True:
                self.log.error("Indrajala connection data not initialized, please provide at least an uri!")
            return None
        if self.use_ssl is True:
            ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            if self.ca_authority is not None:
                ssl_ctx.load_verify_locations(cafile=self.ca_authority)
        websocket = await websockets.connect(self.url, ssl=ssl_ctx)
        return websocket

async def tester():
    cl = IndraClient(config_file="indra_client.toml")
    websocket = await cl.init_connection(verbose=True)
    if websocket is None:
        logging.error("Could not connect to Indrajala")
        return
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

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.get_event_loop().run_until_complete(tester())