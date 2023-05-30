import os
import logging
import asyncio
import socket
import ssl
import websockets
import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo

# XXX dev only
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))

from indralib.indra_event import IndraEvent


class EventProcessor:
    def __init__(self, indra_data, config_data):
        self.log = logging.getLogger("IndraWebsockets")
        self.name = config_data["name"]
        try:
            self.loglevel = config_data["loglevel"].upper()
        except Exception as e:
            self.loglevel = logging.INFO
            logging.error(
                f"Missing entry 'loglevel' in indrajala.toml section {self.name}: {e}"
            )
        self.log.setLevel(self.loglevel)
        # self.toml_data = toml_data
        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.use_ssl = config_data["ssl"]
        self.port = config_data["port"]
        self.bind_address = config_data["bind_address"]
        config_dir = indra_data["config_dir"]
        hostname = socket.gethostname()
        if hostname.find(".") >= 0:
            hostname = hostname.split(".")[0]
        self.active = False
        self.enabled = False
        self.sessions = []
        self.session_id = 0
        if self.use_ssl is True:
            cf = config_data["ssl_certfile"].replace(
                "{configdir}", str(config_dir)).replace("{hostname}", hostname)
            kf = config_data["ssl_keyfile"].replace(
                "{configdir}", str(config_dir)).replace("{hostname}", hostname)
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
            self.req_queue = asyncio.Queue()
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
        self.log.info(
            f"Async init websockets: starting serve at {self.bind_address}:{self.port}"
        )
        self.start_server = websockets.serve(
            self.get_request, self.bind_address, self.port, ssl=self.ssl_context
        )
        return ["$event/#"]

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
            self.sessions.remove(session)

    async def get_request(self, websocket, path):
        connected = True
        session = self._create_session(websocket, path)
        self.log.info(f"WS-recv: New session {session['id']} from {websocket.remote_address}")
        async for message in websocket:
            try:
                req = await websocket.recv()
            except Exception as e:
                self.log.error(f"WS-recv: {e}")
                connected = False
                break
            self.req_queue.put_nowait((req, id))
        self._close_session(session["id"])
        self.log.info(f"WS-recv: Session {session['id']} from {websocket.remote_address} closed")

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

        try:
            ie = json.loads(req[0])
        except Exception as e:
            self.log.error(f"WS-recv: Couldn't decode json of {req}, {e}")
            return {}
        remote_address = self._session_by_id(req[1])["websocket"].remote_address
        ie.from_id = f"{self.name}/{remote_address}"
        return ie

    async def put(self, ie: IndraEvent):
        if self.active is False:
            return
        self.log.info(f"WS-send: {ie}")
        if ie.domain == "$cmd/quit":
            self.log.info("WS-recv: Quit command received")
            n = 0
            for session in self.sessions:
                ie = IndraEvent()
                ie.domain = "$cmd/quit"
                await session["websocket"].send(ie.to_json())
                await session["websocket"].close()
                n += 1
            self.log.info(f"WS-recv: Closed {n} sessions, exiting.")
            return
        for session in self.sessions:
            # XXX subscription handling!
            # await session["websocket"].send(ie.to_json())
            self.info(f"WS-send: {ie} to {session['websocket']['remote_address']}")
        return
