import asyncio
import websockets
import logging
import ssl
import uuid
import toml
import datetime
import os

from indra_event import IndraEvent

class IndraClient:
    def __init__(self, uri=None, ca_authority=None, auth_token=None, config_file="indra_client.toml"):
        self.log = logging.getLogger("IndraClient")
        self.websocket = None
        self.initialized = False
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
        elif uri.startswith("ws://"):
                self.use_ssl = False
        else:
            self.initialized = False
            self.log.error("Please provide a valid uri, starting with ws:// or wss://, e.g. wss://localhost:8082")
            return
    
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
            if os.path.exists(config["ca_authority"]) is False:
                if verbose is True:
                    self.log.error(f"CA authority file {config['ca_authority']} not found!")
                return False
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
            self.websocket = None
            if verbose is True:
                self.log.error("Indrajala connection data not initialized, please provide at least an uri!")
            return None
        if self.use_ssl is True:
            ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            if self.ca_authority is not None:
                try:
                    ssl_ctx.load_verify_locations(cafile=self.ca_authority)
                except Exception as e:
                    self.log.error(f"Could not load CA authority file {self.ca_authority}: {e}")
                    self.websocket = None
                    return None
        try:
            self.websocket = await websockets.connect(self.uri, ssl=ssl_ctx)
        except Exception as e:
            self.log.error(f"Could not connect to {self.uri}: {e}")
            self.websocket = None
            return None
        return self.websocket
    
    async def send_event(self, event):
        """Send event"""
        if self.initialized is False:
            self.log.error("Indrajala connection data not initialized, please provide at least an uri!")
            return False
        if self.websocket is None:
            self.log.error("Websocket not initialized, please call init_connection() first!")
            return False
        if isinstance(event, IndraEvent) is False:
            self.log.error("Please provide an IndraEvent object!")
            return False
        await self.websocket.send(event.to_json())
        return True
    
    async def recv_event(self):
        """Receive event"""
        if self.initialized is False:
            self.log.error("Indrajala connection data not initialized, please provide at least an uri!")
            return None
        if self.websocket is None:
            self.log.error("Websocket not initialized, please call init_connection() first!")
            return None
        try:
            message = await self.websocket.recv()
        except Exception as e:
            self.log.error(f"Could not receive message: {e}")
            return None
        ie = IndraEvent()
        ie.from_json(message)
        return ie
    
    async def close_connection(self):
        """Close connection"""
        if self.initialized is False:
            self.log.error("Indrajala connection data not initialized, please provide at least an uri!")
            return False
        if self.websocket is None:
            self.log.error("Websocket not initialized, please call init_connection() first!")
            return False
        await self.websocket.close()
        self.websocket = None
        return True
    

async def tester():
    cl = IndraClient(config_file="indra_client.toml")
    ws = await cl.init_connection(verbose=True)
    if ws is None:
        logging.error("Could not connect to Indrajala")
        return
    ie = IndraEvent()
    ie.domain = "$event/python/test"
    ie.from_id = "ws/python"
    await cl.send_event(ie)

    while True:
        ie = await cl.recv_event()
        if ie is None:
            logging.error("Could not receive event")
            break
        logging.info(f"Received event: {ie.to_json()}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.get_event_loop().run_until_complete(tester())