import asyncio
import ssl
import aiohttp
from aiohttp import web
import json
import os

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
        self.web_root = os.path.expanduser(self.config_data["web_root"])
        self.static_apps = self.config_data["static_apps"]
        self.static_apps.append(("/indralib", os.path.join(self.web_root, "indralib")))
        self.static_apps.append(
            ("/resources", os.path.join(self.web_root, "resources"))
        )
        self.static_apps.append(("/scripts", os.path.join(self.web_root, "scripts")))
        self.static_apps.append(("/fonts", os.path.join(self.web_root, "fonts")))
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
        self.app.add_routes([web.get("/favicon.ico", self.web_root_handler)])
        for static_app in self.static_apps:
            prefix = static_app[0]
            path = static_app[1]
            if os.path.exists(path) is False:
                self.log.error(
                    f"Static app path does not exist: {path}, did you deploy_web.sh?"
                )
                continue
            self.log.info(f"Adding static app: {prefix} -> {path}")
            self.app.add_routes([web.static(prefix, path)])
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
        # Serve index.html or favicon.ico
        if request.path == "/favicon.ico":
            return web.FileResponse(os.path.join(self.web_root, "favicon.ico"))
        else:
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
                    if IndraEvent.mqcmp(ev.domain, "$trx/kv/req/login") is False:
                        if self.ws_clients[client_address]["session_id"] is None:
                            self.log.warning(
                                f"WS client {client_address} not logged in, ignoring event"
                            )
                            rev = IndraEvent()
                            rev.from_id = f"{self.name}/ws/{client_address}"
                            rev.to_scope = ev.domain
                            rev.domain = ev.from_id
                            rev.uuid4 = ev.uuid4
                            rev.data_type = "error/access"
                            rev.data = json.dumps("Not logged in")
                            await ws.send_str(rev.to_json())
                            continue
                        elif (
                            ev.auth_hash
                            != self.ws_clients[client_address]["session_id"]
                        ):
                            self.log.warning(
                                f"WS client {client_address} session mismatch, ignoring event"
                            )
                            rev = IndraEvent()
                            rev.from_id = f"{self.name}/ws/{client_address}"
                            rev.to_scope = ev.domain
                            rev.domain = ev.from_id
                            rev.uuid4 = ev.uuid4
                            rev.data_type = "error/access"
                            rev.data = json.dumps("Session mismatch")
                            await ws.send_str(rev.to_json())
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
                    self.event_send(ev)
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

        if self.ws_clients[client_address]["session_id"] is not None:
            self.log.warning(
                f"WS-CLOSE: {client_address}, session {self.ws_clients[client_address]['session_id']} was still active, logging out"
            )
            ev = IndraEvent()
            ev.from_id = f"{self.name}/ws/{client_address}"
            ev.domain = "$trx/kv/req/logout"
            ev.auth_hash = self.ws_clients[client_address]["session_id"]
            self.event_send(ev)
        else:
            self.log.warning(f"WS-CLOSE: {client_address}")
        self.ws_clients.pop(client_address, None)  # Delete key ws
        return ws

    async def async_outbound(self, ev: IndraEvent):
        self.log.info(f"WS outbound (pre-route): {ev.domain} from {ev.from_id}")
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
                if ev.to_scope == "$trx/kv/req/logout":
                    self.ws_clients[client_address]["session_id"] = None
                    self.log.info(f"WS client {client_address} logged out")

                await ws.send_str(ev.to_json())

    async def async_shutdown(self):
        # XXX Cleanup!
        pass
