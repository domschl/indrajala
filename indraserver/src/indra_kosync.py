import asyncio
import ssl
import aiohttp
from aiohttp import web
import json
import os
import time

from indralib.indra_event import IndraEvent  # type: ignore
from indra_serverlib import IndraProcessCore


class IndraProcess(IndraProcessCore):
    def __init__(
        self,
        config_data,
        transport,
        event_queue,
        send_queue,
        zmq_event_queue_port,
        zmq_send_queue_port,
    ):
        super().__init__(
            config_data,
            transport,
            event_queue,
            send_queue,
            zmq_event_queue_port,
            zmq_send_queue_port,
            mode="async",
        )

    async def async_init(self):
        self.port = self.config_data["port"]
        self.bind_addresses = self.config_data["bind_addresses"]
        self.private_key = None
        self.public_key = None
        self.reading_state = {}
        self.state_file = self.config_data["state_file"]
        # Create directory if it does not exist
        if not os.path.exists(os.path.dirname(self.state_file)):
            os.makedirs(os.path.dirname(self.state_file))
        if os.path.exists(self.state_file):
            with open(self.state_file, "r") as f:
                self.reading_state = json.load(f)
        self.tls = False
        if self.config_data["tls"] is True:
            if os.path.exists(self.config_data["private_key"]) is False:
                self.log.error(
                    f"Private key file {self.config_data['private_key']} does not exist"
                )
            elif os.path.exists(self.config_data["public_key"]) is False:
                self.log.error(
                    f"Public key file {self.config_data['public_key']} does not exist"
                )
            else:
                self.private_key = self.config_data["private_key"]
                self.public_key = self.config_data["public_key"]
                self.tls = True
        self.app = web.Application(debug=True)
        self.app.add_routes([web.get("/", self.web_root_handler)])
        self.app.add_routes([web.post("/users/create", self.user_create_handler)])
        self.app.add_routes([web.get("/users/auth", self.user_auth_handler)])
        self.app.add_routes(
            [web.get("/syncs/progress/{document}", self.syncs_get_progress_handler)]
        )
        self.app.add_routes(
            [web.put("/syncs/progress", self.syncs_put_progress_handler)]
        )
        self.app.add_routes([web.get("/healthcheck", self.healthcheck_handler)])
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
        self.log.debug("Starting web runner")
        if self.tls is True:
            self.log.debug(f"TLS active, bind={self.bind_addresses}, port={self.port}")
            # print(f"Webclient at: https://localhost:{self.port}")
            site = web.TCPSite(
                runner, self.bind_addresses, self.port, ssl_context=self.ssl_context
            )
        else:
            self.log.debug(
                f"TLS NOT active, bind={self.bind_addresses}, port={self.port}"
            )
            site = web.TCPSite(runner, self.bind_addresses, self.port)
        await site.start()
        if self.tls is True:
            self.log.info(
                f"KOSync active (TLS), bind={self.bind_addresses}, port={self.port}"
            )
        else:
            self.log.info(
                f"KOSync active (no TLS), bind={self.bind_addresses}, port={self.port}"
            )
        while self.bActive:
            await asyncio.sleep(0.1)
        self.log.info("KOSync server stopped")

    def _save_state(self):
        with open(self.state_file, "w") as f:
            json.dump(self.reading_state, f)

    def web_root_handler(self, request):
        return web.Response(text="KOSync server")

    async def user_create_handler(self, request):
        data = await request.json()
        if "username" not in data:
            return web.json_response({"error": "No username in request"}, status=400)
        self.log.debug(f"User create request: {data["username"]}")
        if data["username"] in self.reading_state:
            return web.json_response({"error": "User already exists"}, status=400)
        self.reading_state[data["username"]] = {"password": data["password"], "documents": {}}
        self._save_state()
        return web.json_response({"username": data["username"]}, status=201)

    def _auth(self, request):
        headers = request.headers
        self.log.debug(f"User auth request: {headers}")
        if "x-auth-user" not in headers:
            return web.json_response({"error": "No username in request"}, status=400)
        if "x-auth-key" not in headers:
            return web.json_response({"error": "No password in request"}, status=400)
        if headers["x-auth-user"] not in self.reading_state:
            return web.json_response({"error": "Authentication failure (UNE)"}, status=400)
        if headers["x-auth-key"] != self.reading_state[headers["x-auth-user"]]["password"]:
            return web.json_response({"error": "Authentication failure (PWF)"}, status=401)
        return None

    async def user_auth_handler(self, request):
        ret = self._auth(request)
        if ret is None:
            return web.json_response({"authorized": "OK"}, status=200)
        return ret

    async def syncs_get_progress_handler(self, request):
        ret = self._auth(request)
        if ret is not None:
            return ret
        document = request.match_info["document"]
        self.log.debug(f"Syncs get progress request: {document}")
        user_info = self.reading_state[request.headers["x-auth-user"]]
        if document not in user_info["documents"]:
            progress = {
                "document": document,
                "progress": "0",
                "percentage": 0.0,
                "device": "none",
            }
            self.reading_state[request.headers["x-auth-user"]]["documents"][document] = progress
            self._save_state()
        else:
            progress = user_info["documents"][document]
        return web.json_response(progress)

    async def syncs_put_progress_handler(self, request):
        ret = self._auth(request)
        if ret is not None:
            return ret
        data = await request.json()
        self.log.debug(f"Syncs put progress request: {data}")
        self.reading_state[request.headers["x-auth-user"]]["documents"][data["document"]] = data
        self._save_state()
        return web.json_response({"document": data["document"], "timestamp": time.time()}, status=200)

    async def healthcheck_handler(self, request):
        return web.json_response({"state": "OK"}, status=200)
    
    async def async_outbound(self, ev: IndraEvent):
        pass

    async def async_shutdown(self):
        # XXX Cleanup!
        pass
