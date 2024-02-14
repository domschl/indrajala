import asyncio
import websockets
import logging
import ssl
import json

try:
    import tomllib as toml
except ImportError:
    import tomli as toml

import os
import time
import sys

from indra_event import IndraEvent


class IndraClient:
    def __init__(
        self,
        uri=None,
        ca_authority=None,
        auth_token=None,
        config_file=None,
        verbose=False,
        module_name=None,
        profile="default",
        log_handler=None,
    ):
        self.log = logging.getLogger("IndraClient")
        if log_handler is not None:
            self.log.addHandler(log_handler)
        if module_name is None:
            self.module_name = "IndraClient (python)"
        else:
            self.module_name = module_name
        self.websocket = None
        self.verbose = verbose
        self.trx = {}
        self.recv_queue = asyncio.Queue()
        self.recv_task = None
        self.initialized = False
        if profile is not None and profile.lower() in ["default", "none"]:
            profile = None
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
            else:
                self.use_ssl = False
        elif profile is not None:
            if os.path.exists("/var/lib/indrajala/config") is True:
                cfg_path = "/var/lib/indrajala/config"
            else:
                cfg_path = "~/.config/indrajala/server_profiles"
                cfg_path = os.path.expanduser(cfg_path)
            config_file = os.path.join(cfg_path, profile + ".toml")
            if os.path.exists(config_file) is True:
                self.initialized = self.get_config(config_file, verbose=self.verbose)
            else:
                self.initialized = False
                if verbose is True:
                    self.log.error(
                        f"Profile {profile} not found in {cfg_path}, alternatively please provide a valid uri, starting with ws:// or wss://, e.g. wss://localhost:8082, or config_file=..."
                    )
                return
        else:
            if os.path.exists("/var/lib/indrajala/config/server_profiles") is True:
                cfg_path = "/var/lib/indrajala/config/server_profiles"
            else:
                cfg_path = "~/.config/indrajala/server_profiles"
                cfg_path = os.path.expanduser(cfg_path)
            prfs = IndraClient.get_profiles()

            print(f"Profiles: {prfs}")

            if len(prfs) > 0:
                self.initialized = self.get_config(
                    os.path.join(cfg_path, prfs[0] + ".toml"), verbose=self.verbose
                )
            else:
                self.initialized = False
                if verbose is True:
                    self.log.error(f"No valid profiles found in {cfg_path}")
                return

    @staticmethod
    def get_profiles(prefer_ssl=None):
        """Get profiles"""
        if os.path.exists("/var/lib/indrajala/config/server_profiles") is True:
            cfg_path = "/var/lib/indrajala/config/server_profiles"
        else:
            cfg_path = "~/.config/indrajala/server_profiles"
            cfg_path = os.path.expanduser(cfg_path)
        if os.path.exists(cfg_path) is False:
            return []
        profiles = []
        for f in os.listdir(cfg_path):
            if f.endswith(".toml"):
                if prefer_ssl is None:
                    profiles.append(f[:-5])
                else:
                    try:
                        with open(os.path.join(cfg_path, f), "rb") as f:
                            config = toml.load(f)
                        if "uri" in config:
                            if prefer_ssl is True and config["uri"].startswith(
                                "wss://"
                            ):
                                profiles.append(f[:-5])
                            elif prefer_ssl is False and config["uri"].startswith(
                                "ws://"
                            ):
                                profiles.append(f[:-5])
                    except Exception as e:
                        pass
        return profiles

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
            cert_auth = os.path.expanduser(config["ca_authority"])
            if os.path.exists(cert_auth) is False:
                if verbose is True:
                    self.log.error(f"CA authority file {cert_auth} not found!")
                return False
            self.ca_authority = cert_auth
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
        if verbose is True:
            self.log.info(
                f"Initialized IndraClient with uri={self.uri}, ca_authority={self.ca_authority}, auth_token={self.auth_token}"
            )
        self.initialized = True
        return True

    async def init_connection(self, verbose=False):
        """Initialize connection"""
        if self.initialized is False:
            self.trx = {}
            self.websocket = None
            if verbose is True:
                self.log.error(
                    "Indrajala init_connection(): connection data not initialized!"
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
        self.session_id = None
        self.username = None
        return self.websocket

    async def fn_recv_task(self):
        """Receive task"""
        while True:
            try:
                message = await self.websocket.recv()
                if self.verbose is True:
                    self.log.info(f"Received message: {message}")
            except Exception as e:
                self.log.error(f"Could not receive message: {e}, exiting recv_task()")
                self.recv_task = None
                return False
            # ie = IndraEvent()
            ie = IndraEvent.from_json(message)
            if ie.uuid4 in self.trx:
                fRec = self.trx[ie.uuid4]
                dt = time.time() - fRec["start_time"]
                if self.verbose is True:
                    self.log.info(
                        "---------------------------------------------------------------"
                    )
                    self.log.info(
                        f"Future: trx event {ie.to_scope}, uuid: {ie.uuid4}, {ie.data_type}, dt={dt}"
                    )
                fRec["future"].set_result(ie)
                del self.trx[ie.uuid4]
            else:
                if self.verbose is True:
                    self.log.info(
                        f"Received event {ie.to_scope}, uuid: {ie.uuid4}, {ie.data_type}"
                    )
                await self.recv_queue.put(ie)
        self.recv_task = None
        return

    async def send_event(self, event):
        """Send event"""
        if self.initialized is False:
            self.log.error("Indrajala send_event(): connection data not initialized!")
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
            fRec = {
                "future": replyEventFuture,
                "start_time": time.time(),
            }
            self.trx[event.uuid4] = fRec
            self.log.debug("Future: ", replyEventFuture)
        else:
            replyEventFuture = None
        await self.websocket.send(event.to_json())
        return replyEventFuture

    async def recv_event(self, timeout=None):
        """Receive event"""
        if self.initialized is False:
            self.log.error("Indrajala recv_event(): connection data not initialized!")
            return None
        if self.websocket is None:
            self.log.error(
                "Websocket not initialized, please call init_connection() first!"
            )
            return None
        if timeout is None:
            try:
                ie = await self.recv_queue.get()
            except Exception as e:
                self.log.error(f"Could not receive message: {e}")
                return None
        else:
            try:
                ie = await asyncio.wait_for(self.recv_queue.get(), timeout=timeout)
            except TimeoutError:
                return None
            except Exception as e:
                self.log.warning(f"Timeout receive failed: {e}")
                return None
        self.recv_queue.task_done()
        return ie

    async def close_connection(self):
        """Close connection"""
        if self.initialized is False:
            self.log.error(
                "Indrajala close_connection(): connection data not initialized!"
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
        self.session_id = None
        self.username = None
        return True

    async def subscribe(self, domains):
        """Subscribe to domain"""
        if self.initialized is False:
            self.log.error("Indrajala subscribe(): connection data not initialized!")
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
        ie.auth_hash = self.session_id
        if isinstance(domains, list) is True:
            ie.data = json.dumps(domains)
        else:
            ie.data = json.dumps([domains])
        await self.websocket.send(ie.to_json())
        return True

    async def unsubscribe(self, domains):
        """Unsubscribe from domain"""
        if self.initialized is False:
            self.log.error("Indrajala unsubscribe(): connection data not initialized!")
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
        ie.auth_hash = self.session_id
        if isinstance(domains, list) is True:
            ie.data = json.dumps(domains)
        else:
            ie.data = json.dumps([domains])
        await self.websocket.send(ie.to_json())
        return True

    async def get_history(
        self, domain, start_time=None, end_time=None, sample_size=None, mode="Sample"
    ):
        """Get history of domain

        returns a future object, which will be set when the reply is received
        """
        cmd = {
            "domain": domain,
            "time_jd_start": start_time,
            "time_jd_end": end_time,
            "limit": sample_size,
            # "data_type": "number/float%",
            "mode": mode,
        }
        ie = IndraEvent()
        ie.domain = "$trx/db/req/history"
        ie.from_id = "ws/python"
        ie.data_type = "historyrequest"
        ie.auth_hash = self.session_id
        ie.data = json.dumps(cmd)
        if self.verbose is True:
            self.log.info(f"Sending: {ie.to_json()}")
        return await self.send_event(ie)

    async def get_wait_history(
        self, domain, start_time, end_time=None, sample_size=None, mode="Sample"
    ):
        future = await self.get_history(domain, start_time, end_time, sample_size, mode)
        hist_result = await future
        return json.loads(hist_result.data)

    async def get_last_event(self, domain):
        """Get last event of domain"""
        ie = IndraEvent()
        ie.domain = "$trx/db/req/last"
        ie.from_id = "ws/python"
        ie.data_type = "json/reqlast"
        ie.auth_hash = self.session_id
        ie.data = json.dumps({"domain": domain})
        return await self.send_event(ie)

    async def get_wait_last_event(self, domain):
        future = await self.get_last_event(domain)
        last_result = await future
        if last_result.data is not None and last_result.data != "":
            return IndraEvent.from_json(last_result.data)
        else:
            return None

    async def get_unique_domains(self, domain=None, data_type=None):
        """Get unique domains"""
        if domain is None:
            domain = "$event/%"
        if data_type is None:
            data_type = "%"
        cmd = {
            "domain": domain,
            "data_type": data_type,
        }
        ie = IndraEvent()
        ie.domain = "$trx/db/req/uniquedomains"
        ie.from_id = "ws/python"
        ie.data_type = "uniquedomainsrequest"
        ie.auth_hash = self.session_id
        ie.data = json.dumps(cmd)
        return await self.send_event(ie)

    async def get_wait_unique_domains(self, domain=None, data_type=None):
        future = await self.get_unique_domains(domain, data_type)
        domain_result = await future
        return json.loads(domain_result.data)

    async def delete_recs(self, domains=None, uuid4s=None):
        if domains is None and uuid4s is None:
            self.log.error("Please provide a domain or uuid4s")
            return False
        if domains is not None and uuid4s is not None:
            self.log.error("Please provide either a domain or uuid4s")
            return False
        cmd = {
            "domains": domains,
            "uuid4s": uuid4s,
        }
        ie = IndraEvent()
        ie.domain = "$trx/db/req/del"
        ie.from_id = "ws/python"
        ie.data_type = "json/reqdel"
        ie.auth_hash = self.session_id
        ie.data = json.dumps(cmd)
        return await self.send_event(ie)

    async def delete_recs_wait(self, domains=None, uuid4s=None):
        future = await self.delete_recs(domains, uuid4s)
        result = await future
        if result.data_type.startswith("error") is True:
            self.log.error(f"Error: {result.data}")
            return None
        else:
            return json.loads(result.data)

    async def update_recs(self, recs):
        if isinstance(recs, list) is False:
            print("Not a list")
            recs = [recs]
        cmd = recs
        ie = IndraEvent()
        ie.domain = "$trx/db/req/update"
        ie.from_id = "ws/python"
        ie.data_type = "json/requpdate"
        ie.auth_hash = self.session_id
        ie.data = json.dumps(cmd)
        return await self.send_event(ie)

    async def update_recs_wait(self, recs):
        future = await self.update_recs(recs)
        result = await future
        if result.data_type.startswith("error") is True:
            self.log.error(f"Error: {result.data}")
            return None
        else:
            return json.loads(result.data)

    async def kv_write(self, key, value):
        cmd = {
            "key": key,
            "value": value,
        }
        ie = IndraEvent()
        ie.domain = "$trx/kv/req/write"
        ie.from_id = "ws/python"
        ie.data_type = "kvwrite"
        ie.auth_hash = self.session_id
        ie.data = json.dumps(cmd)
        return await self.send_event(ie)

    async def kv_write_wait(self, key, value):
        future = await self.kv_write(key, value)
        result = await future
        if result.data_type.startswith("error") is True:
            self.log.error(f"Error: {result.data}")
            return None
        else:
            return json.loads(result.data)

    async def kv_read(self, key):
        cmd = {
            "key": key,
        }
        ie = IndraEvent()
        ie.domain = "$trx/kv/req/read"
        ie.from_id = "ws/python"
        ie.data_type = "kvread"
        ie.auth_hash = self.session_id
        ie.data = json.dumps(cmd)
        print("Sending kv_read")
        return await self.send_event(ie)

    async def kv_read_wait(self, key):
        future = await self.kv_read(key)
        print("Waiting for kv_read")
        result = await future
        print("Got kv_read result")
        if result.data_type.startswith("error") is True:
            self.log.error(f"Error: {result.data}")
            return None
        else:
            return json.loads(result.data)

    async def kv_delete(self, key):
        cmd = {
            "key": key,
        }
        ie = IndraEvent()
        ie.domain = "$trx/kv/req/delete"
        ie.from_id = "ws/python"
        ie.data_type = "kvdelete"
        ie.auth_hash = self.session_id
        ie.data = json.dumps(cmd)
        return await self.send_event(ie)

    async def kv_delete_wait(self, key):
        future = await self.kv_delete(key)
        result = await future
        if result.data_type.startswith("error") is True:
            self.log.error(f"Error: {result.data}")
            return None
        else:
            return json.loads(result.data)

    async def login(self, username, password):
        cmd = {
            "key": f"entity/indrajala/user/{username}/password",
            "value": password,
        }
        self.username = username
        ie = IndraEvent()
        ie.domain = "$trx/kv/req/login"
        ie.from_id = "ws/python"
        ie.data_type = "kvverify"
        ie.auth_hash = self.session_id
        ie.data = json.dumps(cmd)
        return await self.send_event(ie)

    async def login_wait(self, username, password):
        future = await self.login(username, password)
        result = await future
        if result.data_type.startswith("error") is True:
            self.log.error(f"Error: {result.data}")
            self.session_id = None
            self.username = None
            return None
        else:
            print(
                f"Login result: {result.data}, {result.data_type}, {result.auth_hash}"
            )
            self.session_id = result.auth_hash
            return result.auth_hash

    async def logout(self):
        ie = IndraEvent()
        ie.domain = "$trx/kv/req/logout"
        ie.from_id = "ws/python"
        ie.auth_hash = self.session_id
        ie.data_type = ""
        ie.data = ""
        return await self.send_event(ie)

    async def logout_wait(self):
        future = await self.logout()
        result = await future
        if result.data_type.startswith("error") is True:
            self.log.error(f"Error: {result.data}")
            return False
        else:
            return True

    async def indra_log(self, level, message, module_name=None):
        """Log message"""
        if module_name is None:
            module_name = self.module_name
        if level not in ["debug", "info", "warn", "error"]:
            self.log.error(f"Invalid log level: {level}, {message}")
            return False
        ie = IndraEvent()
        ie.domain = f"$log/{level}"
        ie.from_id = f"ws/python/{module_name}"
        ie.data_type = "log"
        ie.auth_hash = self.session_id
        ie.data = json.dumps(message)
        return await self.send_event(ie)

    async def debug(self, message, module_name=None):
        self.log.debug(f"Indra_log-Debug: {message}")
        return await self.indra_log("debug", message, module_name)

    async def info(self, message, module_name=None):
        self.log.info(f"Indra_log-Info: {message}")
        return await self.indra_log("info", message, module_name)

    async def warn(self, message, module_name=None):
        self.log.warn(f"Indra_log-Warn: {message}")
        return await self.indra_log("warn", message, module_name)

    async def error(self, message, module_name=None):
        self.log.error(f"Indra_log-Error: {message}")
        return await self.indra_log("error", message, module_name)
