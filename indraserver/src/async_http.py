import asyncio
import ssl
import aiohttp
from aiohttp import web
import json

# XXX dev only
import sys
import os

path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "indralib/src",
)
sys.path.append(path)
from indra_event import IndraEvent  # type: ignore

from indra_serverlib import IndraProcessCore


class IndraProcess(IndraProcessCore):
    def __init__(self, event_queue, send_queue, config_data):
        super().__init__(event_queue, send_queue, config_data, mode="async")

    async def async_init(self):
        self.port = self.config_data["port"]
        self.bind_addresses = self.config_data["bind_addresses"]
        self.web_root = os.path.expanduser(self.config_data["web_root"])
        self.private_key = None
        self.public_key = None
        self.ws_clients = {}
        self.tr_id = 0
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
        # if self.tls is True:
        #     self.app.add_routes([web.get('/wss', self.websocket_handler)])
        # else:
        self.app.add_routes([web.get("/ws", self.websocket_handler)])
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
            # print(f"Webclient at: http://localhost:{self.port}")
        await site.start()
        if self.tls is True:
            self.log.info(
                f"Web+Websockets active (TLS), bind={self.bind_addresses}, port={self.port}"
            )
        else:
            self.log.info(
                f"Web+Websockets active (no TLS), bind={self.bind_addresses}, port={self.port}"
            )
        while self.bActive:
            await asyncio.sleep(0.1)
        self.log.info("Web server stopped")

    def web_root_handler(self, request):
        return web.FileResponse(os.path.join(self.web_root, "index.html"))

    async def websocket_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        client_remote_address = request.remote
        cur_tr_id = self.tr_id
        client_address = f"{client_remote_address}/{cur_tr_id}"
        self.tr_id += 1
        self.log.info(f"WS Client: {client_address}")
        if client_address not in self.ws_clients:
            self.ws_clients[client_address] = {
                "ws": ws,
                "from_id": None,
                "user_id": None,
                "session_id": None,
                "subs": [],
            }
            self.log.info(
                f"New ws client {client_address}! (num clients: {len(self.ws_clients)})"
            )
        else:
            fid = self.ws_clients[client_address].get("from_id", "None")
            self.thread_log.warning(
                f"Client {client_address} already registered! Num clients: {len(self.ws_clients)}, from_id: {fid}"
            )

        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                # if msg.data is not None:
                self.log.debug("Client ws_dispatch: ws:{} msg:{}".format(ws, msg.data))
                try:
                    ev = IndraEvent.from_json(msg.data)
                    if (
                        self.ws_clients[client_address]["session_id"] is None
                        and IndraEvent.mqcmp(ev.domain, "$trx/kv/req/login") is False
                    ):
                        self.log.warning(
                            f"WS client {client_address} not logged in, ignoring event"
                        )
                        continue
                    self.ws_clients[client_address]["old_from_id"] = ev.from_id
                    ev.from_id = f"{self.name}/ws/{client_address}"
                    self.ws_clients[client_address]["from_id"] = ev.from_id
                    self.log.info(
                        f"Received (upd.): {client_address}: {ev.from_id}->{ev.domain}"
                    )
                    if ev.domain == "$cmd/subs":
                        new_subs = json.loads(ev.data)
                        for new_sub in new_subs:
                            self.ws_clients[client_address]["subs"].append(
                                new_sub
                            )  # allow dups
                    elif ev.domain == "$cmd/unsubs":
                        new_unsubs = json.loads(ev.data)
                        for new_unsub in new_unsubs:
                            self.ws_clients[client_address]["subs"].remove(new_unsub)
                    self.event_queue.put(ev)
                except Exception as e:
                    self.log.warning(f"WebClient sent invalid JSON: {msg.data}: {e}")
            elif msg.type == aiohttp.WSMsgType.ERROR:
                self.log.warning(
                    f"ws connection closed with exception {ws.exception()}"
                )
                break
            else:
                self.log.error(f"Unexpected message {msg.data}, of type {msg.type}")
                break
        self.log.warning(f"WS-CLOSE: {client_address}")
        self.ws_clients.pop(client_address, None)  # Delete key ws
        return ws

    async def async_outbound(self, ev: IndraEvent):
        self.log.debug(f"WS outbound: {ev.domain} from {ev.from_id}")
        for client_address in self.ws_clients:
            ws = self.ws_clients[client_address]["ws"]
            route = False
            if ev.domain.endswith(client_address):
                route = True
            else:
                for sub in self.ws_clients[client_address]["subs"]:
                    if IndraEvent.mqcmp(ev.domain, sub):
                        route = True
                        break
            if route is True:
                self.log.info(
                    f"Sending to ws-client: {client_address}, dom: {ev.domain}, scope: {ev.to_scope}, ws_from_id: {self.ws_clients[client_address]['from_id']}"
                )
                if (
                    ev.to_scope == "$trx/kv/req/login"
                    and ev.data_type.startswith("error") is False
                    and ev.auth_hash is not None
                    and ev.auth_hash != ""
                ):
                    self.ws_clients[client_address]["session_id"] = ev.auth_hash
                    self.log.info(
                        f"WS client {client_address} logged in, session_id: {ev.auth_hash}"
                    )

                await ws.send_str(ev.to_json())

    async def async_shutdown(self):
        # XXX Cleanup!
        pass
