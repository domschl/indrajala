import os
import logging
import asyncio
import ssl
import websockets
import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo


class EventProcessor:
    def __init__(self, name, toml_data):
        self.log = logging.getLogger("IndraWebsockets")
        try:
            self.loglevel = toml_data[name]["loglevel"].upper()
        except Exception as e:
            self.loglevel = logging.INFO
            logging.error(
                f"Missing entry 'loglevel' in indrajala.toml section {name}: {e}"
            )
        self.log.setLevel(self.loglevel)
        self.toml_data = toml_data
        self.name = name
        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.use_ssl = toml_data["in_async_websockets"]["ssl"]
        self.port = toml_data["in_async_websockets"]["port"]
        self.bind_address = toml_data["in_async_websockets"]["bind_address"]
        config_dir = toml_data["indrajala"]["config_dir"]
        self.active = False
        self.enabled = False
        self.sessions = []
        self.session_id = 0
        if self.use_ssl is True:
            cf = toml_data["in_async_websockets"]["ssl_certfile"].replace(
                "{configdir}", str(config_dir)
            )
            kf = toml_data["in_async_websockets"]["ssl_keyfile"].replace(
                "{configdir}", str(config_dir)
            )
            if os.path.exists(cf) is False:
                self.log.error(f"certfile {cf} does not exist!")
                return
            if os.path.exists(kf) is False:
                self.log.error(f"keyfile {kf} does not exist!")
                return
            try:
                self.ssl_context.load_cert_chain(certfile=cf, keyfile=kf)
                self.req_queue = asyncio.Queue()
                self.active = True
            except Exception as e:
                self.log.error(f"Failed to read ssl certs: {e}")
        else:
            self.active = True
        return

    def isActive(self):
        return self.active

    async def server_task(self):
        stop = asyncio.Future()
        await self.start_server
        self.log.debug("Websockets server started.")
        self.online_future.set_result(0)
        self.enabled = True
        await stop
        self.log.debug("Websockets: Terminated")

    async def async_init(self, loop):
        if self.active is False:
            return []
        self.loop = loop
        self.online_future = asyncio.Future()

        # async with websockets.serve(self.get_request, self.bind_address, self.port, ssl=self.ssl_context):
        #     await asyncio.Future();  # run forever
        self.log.debug(
            f"Async init websockets: starting serve at {self.bind_address}:{self.port}"
        )
        self.start_server = websockets.serve(
            self.get_request, self.bind_address, self.port, ssl=self.ssl_context
        )
        return ["#"]

    def _create_session(self, websocket, path):
        session = {
            "id": self.session_id,
            "path": path,
            "websocket": websocket,
            "time": time.time(),
        }
        self.session_id += 1
        self.sessions.append(session)
        return session

    def _session_by_id(self, id):
        for session in self.sessions:
            if session["id"] == id:
                return session
        return None

    def _close_session(self, id):
        session = self._session_by_id(id)
        if session is None:
            self.log.warning(f"Tried to close nonexisting session {id}")
        else:
            # await session['websocket'].close()
            session["websocket"].close()

    async def get_request(self, websocket, path):
        req = await websocket.recv()
        session = self._create_session(websocket, path)
        self.req_queue.put_nowait((req, id))

    async def get(self):
        if self.active is False:
            self.log.error(
                "websockets are not active (failed to init?) and receive get()"
            )
            return {}
        if self.enabled is False:
            await self.online_future
        req = await self.req_queue.get()
        self.req_queue.task_done()
        default_toks = {
            "cmd": "ping",
            "origin": self.name,
            "time": datetime.now(tz=ZoneInfo("UTC")),
            "topic": "ws",
            "body": "",
        }
        msg = {}
        if req and len(req) > 0 and req[0] == "{":
            try:
                msg = json.loads(req)
            except Exception as e:
                self.log.error(f"WS-recv: Couldn't decode json of {req}, {e}")
        for tok in default_toks:
            if tok not in msg:
                self.log.warning(
                    f"Required token {tok} not in msg obj {msg}, setting {tok}={default_toks[tok]}"
                )
                msg[tok] = default_toks[tok]
        return msg

    async def put(self, msg):
        if self.active is False:
            return
        return