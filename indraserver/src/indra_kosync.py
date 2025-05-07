import asyncio
import ssl
from aiohttp import web  # type: ignore
import json
import os
import time
import hashlib

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
        self.library_state = []
        self.sequence_number = 0
        self.state_file = self.config_data["state_file"]
        # Create directory if it does not exist
        if not os.path.exists(os.path.dirname(self.state_file)):
            os.makedirs(os.path.dirname(self.state_file))
        if os.path.exists(self.state_file):
            with open(self.state_file, "r") as f:
                self.reading_state = json.load(f)
        self.library_state_filename = os.path.expanduser(self.config_data["library_state_file"])
        self._update_library_state()
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

        if 'repo_state_update_condition' in self.config_data:
            self.repo_state_update_condition = self.config_data['repo_state_update_condition']
        else:
            self.repo_state_update_condition = "periodic@3m"
            self.log.info(f"Using default repo_state_update_condition: {self.repo_state_update_condition}")
        self.create_timer_thread("repo_state_update", self.repo_state_update_condition, self._update_library_state)

    def _update_library_state(self):
        self.md5_to_lib_entry = {}
        self.library_state = []
        old_sequence_number = self.sequence_number
        if os.path.exists(self.library_state_filename):
            with open(self.library_state_filename, "r") as f:
                repo_state = json.load(f)
                self.library_state = repo_state['lib_entries']
                self.sequence_number = repo_state['sequence_number']
                if self.sequence_number == old_sequence_number:
                    self.log.info(f"Library state file {self.library_state_filename} has not changed")
                    return
                else:
                    self.log.info(f"Library state file {self.library_state_filename} has changed, updating.")
        else:
            self.log.error(f"Library state file {self.library_state_filename} does not exist")
            return
        for lib_entry in self.library_state:
            if 'uuid' in lib_entry:
                uuid = lib_entry['uuid']
            else:
                self.log.error(f"Library entry {lib_entry} has no UUID")
                continue
            if 'docs' in lib_entry:
                for doc in lib_entry['docs']:
                    fn = doc['ref_name']
                    md5_hash = hashlib.md5(fn.encode('utf-8')).hexdigest()
                    self.md5_to_lib_entry[md5_hash] = {'filename': fn, 'uuid': uuid}
                    # Get MD5 of file content:
                    with open(fn, "rb") as f:
                        file_content = f.read()
                        md5_hash = hashlib.md5(file_content).hexdigest()
                        self.md5_to_lib_entry[md5_hash] = {'filename': fn, 'uuid': uuid}
            else:
                self.log.warning(f"Document {lib_entry} has no docs")
        self.log.info(f"Library size: {len(self.md5_to_lib_entry)}")

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
            self.log.error("No username in request")    
            return web.json_response({"error": "No username in request"}, status=400)
        if data["username"] in self.reading_state:
            self.log.error(f"User {data["username"]} already exists")
            return web.json_response({"error": "User already exists"}, status=400)
        self.reading_state[data["username"]] = {"password": data["password"], "documents": {}}
        self.log.info(f"User create request: {data["username"]}")
        self._save_state()
        return web.json_response({"username": data["username"]}, status=201)

    def _auth(self, request):
        headers = request.headers
        self.log.debug(f"User auth request: {headers}")
        if "x-auth-user" not in headers:
            self.log.error("No username in request")
            return web.json_response({"error": "No username in request"}, status=400), None
        if "x-auth-key" not in headers:
            self.log.error("No password in request")
            return web.json_response({"error": "No password in request"}, status=400), None
        if headers["x-auth-user"] not in self.reading_state:
            self.log.error(f"User {headers["x-auth-user"]} not found")
            return web.json_response({"error": "Authentication failure (UNE)"}, status=400), None
        if headers["x-auth-key"] != self.reading_state[headers["x-auth-user"]]["password"]:
            self.log.error(f"User {headers["x-auth-user"]} password mismatch")
            return web.json_response({"error": "Authentication failure (PWF)"}, status=401), None
        self.log.info(f"User {headers["x-auth-user"]} authenticated")
        return None, headers["x-auth-user"]

    async def user_auth_handler(self, request):
        ret, _ = self._auth(request)
        if ret is None:
            return web.json_response({"authorized": "OK"}, status=200)
        return ret

    async def syncs_get_progress_handler(self, request):
        ret, user = self._auth(request)
        if ret is not None or user is None:
            return ret
        document = request.match_info["document"]
        self.log.info(f"Syncs {user} get progress request: {document}")
        user_info = self.reading_state[request.headers["x-auth-user"]]
        if document not in self.md5_to_lib_entry:
            self.log.warning(f"Document {document} not found in library")
        else:
            filename = self.md5_to_lib_entry[document]['filename']
            self.log.info(f"Document {document} is {filename}") 
        if document not in user_info["documents"]:
            progress = {
                "document": document,
                "progress": "0",
                "percentage": 0.0,
                "device": "none",
            }
            self.reading_state[user]["documents"][document] = progress
            self._save_state()
        else:
            progress = user_info["documents"][document]
        return web.json_response(progress)

    async def syncs_put_progress_handler(self, request):
        ret, user = self._auth(request)
        if ret is not None:
            return ret
        data = await request.json()
        document = data["document"]
        self.log.info(f"Syncs put {user} progress request for document {document}: {data}")
        self.reading_state[request.headers["x-auth-user"]]["documents"][document] = data
        if document not in self.md5_to_lib_entry:
            self.log.warning(f"Document {document} not found in MetaLibrary, progress not saved as user-event")
        else:
            filename = self.md5_to_lib_entry[document]['filename']
            uuid = self.md5_to_lib_entry[document]['uuid']
            self.log.info(f"Document {document}, user {user} is {filename}") 
            reading_progress = {
                "filename": filename,
                "uuid": uuid,
                "progress": data["progress"],
                "percentage": data["percentage"],
                "device": data["device"],
            }
            domain = f"$event/books/reading_progress/{user}/{uuid}"
            ev = IndraEvent()
            ev.domain = domain
            ev.from_id = self.name
            ev.to_scope = f"private/user/{user}"
            ev.data_type = "json/reading_progress"
            ev.data = json.dumps(reading_progress)
            self.event_send(ev)
        self._save_state()
        return web.json_response({"document": data["document"], "timestamp": time.time()}, status=200)

    async def healthcheck_handler(self, request):
        return web.json_response({"state": "OK"}, status=200)
    
    async def async_outbound(self, ev: IndraEvent):
        pass

    async def async_shutdown(self):
        # XXX Cleanup!
        pass
