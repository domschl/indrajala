import asyncio
import websockets
import logging
import ssl
import json
import tomllib as toml
import os

from indralib.indra_event import IndraEvent


class IndraClient:
    def __init__(
        self,
        uri=None,
        ca_authority=None,
        auth_token=None,
        config_file=None,
        verbose=True,
    ):
        self.log = logging.getLogger("IndraClient")
        self.websocket = None
        self.verbose = verbose
        self.trx = {}
        self.recv_queue = asyncio.Queue()
        self.recv_task = None
        self.initialized = False
        if config_file is not None and config_file != "":
            self.initialized = self.get_config(config_file, verbose=self.verbose)
        elif uri is not None and uri != "":
            self.initialized = True
            self.uri = uri
            if ca_authority is not None and ca_authority != "":
                self.ca_authority = ca_authority
            else:
                self.ca_authority = None
            if auth_token is not None and auth_token != "":
                self.auth_token = auth_token
            else:
                self.auth_token = None
            if self.uri.startswith("wss://"):
                self.use_ssl = True
        elif uri.startswith("ws://"):
            self.use_ssl = False
        else:
            self.initialized = False
            if verbose is True:
                self.log.error(
                    "Please provide a valid uri, starting with ws:// or wss://, e.g. wss://localhost:8082"
                )
            return

    def get_config(self, config_file, verbose=True):
        """Get config from file"""
        self.initialized = False
        try:
            with open(config_file, "rb") as f:
                config = toml.load(f)
            if verbose is True:
                self.log.debug(f"Loaded config from {config_file}: {config}f")
        except Exception as e:
            if verbose is True:
                self.log.error(f"{config_file} config file not found: {e}")
            return False
        if "uri" not in config:
            if verbose is True:
                self.log.error(
                    f"Please provide an uri=ws[s]://host:port in {config_file}"
                )
            return False
        self.uri = config["uri"]
        if "ca_authority" in config and config["ca_authority"] != "":
            if os.path.exists(config["ca_authority"]) is False:
                if verbose is True:
                    self.log.error(
                        f"CA authority file {config['ca_authority']} not found!"
                    )
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
            self.trx = {}
            self.websocket = None
            if verbose is True:
                self.log.error(
                    "Indrajala connection data not initialized, please provide at least an uri!"
                )
            return None
        if self.websocket is not None:
            if verbose is True:
                self.log.warning(
                    "Websocket already initialized, please call close_connection() first!"
                )
            return self.websocket
        self.trx = {}
        if self.use_ssl is True:
            ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            if self.ca_authority is not None:
                try:
                    ssl_ctx.load_verify_locations(cafile=self.ca_authority)
                except Exception as e:
                    self.log.error(
                        f"Could not load CA authority file {self.ca_authority}: {e}"
                    )
                    self.websocket = None
                    return None
        try:
            self.websocket = await websockets.connect(self.uri, ssl=ssl_ctx)
        except Exception as e:
            self.log.error(f"Could not connect to {self.uri}: {e}")
            self.websocket = None
            return None
        self.recv_queue.empty()
        self.recv_task = asyncio.create_task(self.fn_recv_task())
        return self.websocket

    async def fn_recv_task(self):
        """Receive task"""
        while True:
            try:
                message = await self.websocket.recv()
                if self.verbose is True:
                    self.log.info(f"Received message: {message}")
            except Exception as e:
                self.log.error(f"Could not receive message: {e}")
                break
            # ie = IndraEvent()
            ie = IndraEvent.from_json(message)
            self.log.info(f"Received event: {ie.to_json()}")
            if ie.uuid4 in self.trx:
                if self.verbose is True:
                    self.log.info(f"Future triggered of trx event {ie.uuid4}")
                self.trx[ie.uuid4].set_result(ie)
                del self.trx[ie.uuid4]
            else:
                await self.recv_queue.put(ie)
        self.recv_task = None
        return

    async def send_event(self, event):
        """Send event"""
        if self.initialized is False:
            self.log.error(
                "Indrajala connection data not initialized, please provide at least an uri!"
            )
            return False
        if self.websocket is None:
            self.log.error(
                "Websocket not initialized, please call init_connection() first!"
            )
            return False
        if isinstance(event, IndraEvent) is False:
            self.log.error("Please provide an IndraEvent object!")
            return False
        if event.domain.startswith("$trx/") is True:
            replyEventFuture = asyncio.futures.Future()
            self.trx[event.uuid4] = replyEventFuture
            print("Future: ", replyEventFuture)
        else:
            replyEventFuture = None
        await self.websocket.send(event.to_json())
        return replyEventFuture

    async def recv_event(self):
        """Receive event"""
        if self.initialized is False:
            self.log.error(
                "Indrajala connection data not initialized, please provide at least an uri!"
            )
            return None
        if self.websocket is None:
            self.log.error(
                "Websocket not initialized, please call init_connection() first!"
            )
            return None
        try:
            ie = await self.recv_queue.get()
        except Exception as e:
            self.log.error(f"Could not receive message: {e}")
            return None
        self.recv_queue.task_done()
        return ie

    async def close_connection(self):
        """Close connection"""
        if self.initialized is False:
            self.log.error(
                "Indrajala connection data not initialized, please provide at least an uri!"
            )
            return False
        if self.websocket is None:
            self.log.error(
                "Websocket not initialized, please call init_connection() first!"
            )
            return False
        if self.recv_task is not None:
            self.recv_task.cancel()
            self.recv_task = None
        await self.websocket.close()
        self.trx = {}
        self.websocket = None
        return True

    async def subscribe(self, domains):
        """Subscribe to domain"""
        if self.initialized is False:
            self.log.error(
                "Indrajala connection data not initialized, please provide at least an uri!"
            )
            return False
        if self.websocket is None:
            self.log.error(
                "Websocket not initialized, please call init_connection() first!"
            )
            return False
        if domains is None or domains == "":
            self.log.error("Please provide a valid domain(s)!")
            return False
        ie = IndraEvent()
        ie.domain = "$cmd/subs"
        ie.from_id = "ws/python"
        ie.data_type = "vector/string"
        if isinstance(domains, list) is True:
            ie.data = json.dumps(domains)
        else:
            ie.data = json.dumps([domains])
        await self.websocket.send(ie.to_json())
        return True

    async def unsubscribe(self, domains):
        """Unsubscribe from domain"""
        if self.initialized is False:
            self.log.error(
                "Indrajala connection data not initialized, please provide at least an uri!"
            )
            return False
        if self.websocket is None:
            self.log.error(
                "Websocket not initialized, please call init_connection() first!"
            )
            return False
        if domains is None or domains == "":
            self.log.error("Please provide a valid domain(s)!")
            return False
        ie = IndraEvent()
        ie.domain = "$cmd/unsubs"
        ie.from_id = "ws/python"
        ie.data_type = "vector/string"
        if isinstance(domains, list) is True:
            ie.data = json.dumps(domains)
        else:
            ie.data = json.dumps([domains])
        await self.websocket.send(ie.to_json())
        return True

    async def get_history(self, domain, start_time, end_time=None, sample_size=None):
        """Get history of domain

        returns a future object, which will be set when the reply is received
        """
        cmd = {
            "domain": domain,
            "time_jd_start": start_time,
            "time_jd_end": end_time,
            "max_count": sample_size,
            "mode": "Interval",
        }
        ie = IndraEvent()
        ie.domain = "$trx/db/req/event/history"
        ie.from_id = "ws/python"
        ie.data_type = "eventrequest"
        ie.data = json.dumps(cmd)
        self.log.info(f"Sending: {ie.to_json()}")
        return await self.send_event(ie)

    async def get_wait_history(
        self, domain, start_time, end_time=None, sample_size=None
    ):
        future = await self.get_history(domain, start_time, end_time, sample_size)
        hist_result = await future
        return json.loads(hist_result.data)
