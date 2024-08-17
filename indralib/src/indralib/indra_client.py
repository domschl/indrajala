import asyncio
import websockets
import logging
import ssl
import json
import time
import datetime
from datetime import timezone

from indralib.indra_event import IndraEvent
from indralib.indra_time import IndraTime
from indralib.server_config import Profiles


class IndraClient:
    def __init__(
        self,
        profile=None,
        profile_name="default",
        verbose=False,
        module_name=None,
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
        self.error_shown = False
        self.profiles = Profiles()
        if profile is not None and Profiles.check_profile(profile) is False:
            self.log.error(f"Invalid profile {profile}")
            self.profile = None
            return
        if profile is not None:
            self.profile = profile
            self.initialized = True
        else:
            if profile_name == "default":
                self.profile = self.profiles.get_default_profile()
            else:
                self.profile = self.profiles.get_profile(profile_name)
            if self.profile is not None:
                self.initialized = True

    async def init_connection(self, verbose=False):
        """Initialize connection"""
        if self.initialized is False:
            self.trx = {}
            self.websocket = None
            self.log.error(
                "Indrajala init_connection(): connection profile data not initialized!"
            )
            return None
        if self.websocket is not None:
            if verbose is True:
                self.log.warning(
                    "Websocket already initialized, please call close_connection() first!"
                )
            return self.websocket
        self.trx = {}
        self.uri = Profiles.get_uri(self.profile)
        if self.profile["TLS"] is True:
            ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            if self.profile["ca_authority"] is not None:
                try:
                    ssl_ctx.load_verify_locations(cafile=self.profile["ca_authority"])
                except Exception as e:
                    self.log.error(
                        f"Could not load CA authority file {self.profile['ca_authority']}: {e}"
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
        self.error_shown = False
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
            if self.error_shown is False:
                self.error_shown = True
                self.log.error(
                    "Indrajala send_event(): connection data not initialized!"
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
            fRec = {
                "future": replyEventFuture,
                "start_time": time.time(),
            }
            self.trx[event.uuid4] = fRec
            self.log.debug("Future: ", replyEventFuture)
        else:
            replyEventFuture = None
        try:
            await self.websocket.send(event.to_json())
        except Exception as e:
            self.log.error(f"Could not send message: {e}")
            self.initialized = False
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
        self, domain, start_time=None, end_time=None, sample_size=None, mode="Sample"
    ):
        future = await self.get_history(domain, start_time, end_time, sample_size, mode)
        hist_result = await future
        return json.loads(hist_result.data)

    @staticmethod
    def get_current_time_jd():
        cdt = datetime.datetime.now(timezone.utc)
        dt_jd = IndraTime.datetime2julian(cdt)
        return dt_jd

    @staticmethod
    async def _get_history_block(
        username=None,
        password=None,
        domain=None,
        start_time=None,
        end_time=None,
        verbose=False,
        sample_size=20,
    ):
        ic = IndraClient(verbose=verbose)
        if verbose is True:
            ic.log.info(f"Connecting")
        await ic.init_connection()
        if verbose is True:
            ic.log.info("Connected to Indrajala")
        ret = await ic.login_wait(username, password)
        if verbose is True:
            ic.log.info(f"Login result: {ret}")
        if ret is not None:
            if verbose is True:
                ic.log.info(f"Logged in as {username}")
            data = await ic.get_wait_history(
                domain=domain,
                start_time=start_time,
                end_time=end_time,
                sample_size=sample_size,
                mode="Sample",
            )
            if verbose is True:
                ic.log.info(f"Data: {data}")
            await ic.logout_wait()
            await ic.close_connection()
            if verbose is True:
                ic.log.info("Logged out and closed connection")
            return data
        return None

    @staticmethod
    def get_history_sync(
        username,
        password,
        domain,
        start_time,
        end_time=None,
        sample_size=20,
        verbose=False,
    ):
        return asyncio.run(
            IndraClient._get_history_block(
                username, password, domain, start_time, end_time, verbose, sample_size
            )
        )

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
            self.log.error("Not a list")
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
        self.log.debug("Sending kv_read")
        return await self.send_event(ie)

    async def kv_read_wait(self, key):
        future = await self.kv_read(key)
        result = await future
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
            self.log.debug(
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

    @staticmethod
    def get_timeseries(result):
        dt = []
        y = []
        for t, yv in result:
            dt.append(IndraTime.julian2datetime(t))
            y.append(yv)
        return dt, y
