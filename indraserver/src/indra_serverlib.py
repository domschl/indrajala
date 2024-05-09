import multiprocessing as mp
import queue
import os
import json
import threading
import time
import signal
import asyncio
import zmq

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 and older:
    import tomli as tomllib  # type: ignore
import sys

# path = os.path.join(
#     os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
#     "indralib/src",
# )
# sys.path.append(path)
from indralib.indra_event import IndraEvent  # type: ignore


class IndraServerLog:
    def __init__(
        self: str,
        name,
        transport: str,
        loglevel: str,
        event_queue: queue.Queue = None,
        socket=None,
    ):
        self.loglevels = ["none", "error", "warning", "info", "debug"]
        self.transports = ["zmq", "queue"]
        if transport not in self.transports:
            print(
                f"Invalid transport: {transport}, for IndraServerLog, cannot continue"
            )
            exit(1)
        if loglevel in self.loglevels:
            self.loglevel = self.loglevels.index(loglevel)
        else:
            self.loglevel = self.loglevels.index("info")
        self.name = name
        self.transport = transport
        self.socket = socket
        self.event_queue = event_queue

    def _send_log(self, level, msg):
        self.ev = IndraEvent()
        self.ev.data_type = "string"
        self.ev.from_id = self.name
        self.ev.domain = "$log/" + level
        self.ev.data = msg
        if self.transport == "zmq":
            self.socket.send_json(self.ev.to_dict())
        else:
            self.event_queue.put(self.ev)

    def error(self, msg):
        if self.loglevel > 0:
            self._send_log("error", msg)

    def warning(self, msg):
        if self.loglevel > 1:
            self._send_log("warning", msg)

    def info(self, msg):
        if self.loglevel > 2:
            self._send_log("info", msg)

    def debug(self, msg):
        if self.loglevel > 3:
            self._send_log("debug", msg)


class IndraProcessCore:
    def __init__(
        self,
        config_data,
        transport,
        event_queue=None,
        send_queue=None,
        zmq_event_queue_port=0,
        zmq_send_queue_port=0,
        signal_handler=True,
        mode="dual",
    ):
        """Super-class that is used to instantiate the IndraProcess object
        There are two different transports: 'zmq' and 'queue'. The 'zmq' transport is used for
        inter-process communication and the 'queue' transport is used for Python queue() communication
        using event_queue and send_queue. The 'zmq' transport is used for inter-process communication
        using ports zmq_event_queue_port and zmq_send_queue_port.
        There are three different modes, an IndraProcess can be implemented: 'single', 'dual' and
        'async'.
        In 'single' mode the instance needs to implement outbound() and optionally outbound_init()
        and shutdown() [Example: indra_db].
        In 'dual' mode, an additional thread is started for handling inbound() events. [pingpong]
        In 'async' mode, an async runtime is started and the instance needs to implent async_init(),
        async_outbound() and async_shutdown() [Example: async_http]
        """
        self.name = config_data["name"]
        self.transports = ["zmq", "queue"]
        if transport not in self.transports:
            print(
                f"Invalid transport: {transport}, for IndraProcessCore, cannot continue"
            )
            exit(1)
        self.transport = transport
        if transport == "zmq":
            self.context = zmq.Context()
            self.zmq_event_socket = self.context.socket(zmq.PUSH)
            self.zmq_event_socket_uri = f"tcp://localhost:{zmq_event_queue_port}"
            self.zmq_event_socket.connect(self.zmq_event_socket_uri)
            self.zmq_send_socket = self.context.socket(zmq.PULL)
            self.zmq_send_socket.setsockopt(zmq.RCVTIMEO, 200)
            self.zmq_send_socket_uri = f"tcp://*:{zmq_send_queue_port}"
            self.zmq_send_socket.bind(self.zmq_send_socket_uri)
            self.send_queue = None
            self.event_queue = None
        elif transport == "queue":
            self.send_queue = send_queue
            self.event_queue = event_queue
            self.zmq_event_socket = None
            self.zmq_send_socket = None
        self.log = IndraServerLog(
            self.name,
            transport,
            config_data["loglevel"],
            self.event_queue,
            self.zmq_event_socket,
        )
        self.bActive = True
        self.config_data = config_data
        self.throttle = 0

        if mode not in ["single", "dual", "async"]:
            self.log.error(
                f"Invalid mode={mode}, valid are 'single', 'dual', 'async', setting 'dual'"
            )
            mode = "dual"
        self.mode = mode

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        for sub in config_data["subscriptions"]:
            self.subscribe(sub)

        if transport == "zmq":
            self.log.info(
                f"ZMQ sockets connected: Event: {self.zmq_event_socket_uri}, Send: {self.zmq_send_socket_uri}"
            )

        self.log.info(f"IndraProcess {self.name} instantiated")

    def event_send(self, ev):
        """Send an event to the event queue"""
        if self.transport == "zmq":
            self.zmq_event_socket.send_json(ev.to_dict())
        else:
            self.event_queue.put(ev)

    def event_send_self(self, ev):
        """Send an event to the send queue (incoming to self)"""
        if self.transport == "zmq":
            self.zmq_send_socket.send_json(ev.to_dict())  # XXX Does this work?
        else:
            self.send_queue.put(ev)

    def launcher(self):
        if self.mode == "dual":
            self.sender = threading.Thread(
                target=self.send_worker,
                name=self.name + "_send_worker",
                args=[],
                daemon=True,
            )
            self.sender.start()
        if self.mode == "async":
            self.async_rt = threading.Thread(
                target=self.async_rt_worker,
                name=self.name + "_async_rt_worker",
                args=[],
                daemon=True,
            )
            self.async_rt.start()
        else:
            self.receiver = threading.Thread(
                target=self.receive_worker,
                name=self.name + "_receive_worker",
                args=[],
                daemon=True,
            )
            self.receiver.start()
        self.log.debug(f"Launcher of {self.name} started")
        try:
            while self.bActive:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        self.log.debug(f"Launcher of {self.name} signaled")
        if self.mode == "dual":
            self.sender.join()
        if self.mode == "async":
            self.async_rt.join()
        else:
            self.receiver.join()
        self.log.info(f"Launcher of {self.name} terminating...")

    def is_active(self):
        """Check if module is active"""
        return self.bActive

    def signal_handler(self, sig, frame):
        sys.exit(0)

    def set_throttle(self, throttle):
        """set a minimum pause between messages received from outside"""
        self.throttle = throttle

    def send_worker(self):
        """send_worker (inbound) is active only in 'dual' mode"""
        self.log.debug(f"{self.name} started send_worker")
        if self.inbound_init() is True:
            dt_corr = time.time()
            start = time.time()
            while self.bActive is True:
                dt_corr = time.time() - start
                start = time.time()
                ev = self.inbound()
                if ev is not None:
                    self.event_send(ev)
                    if self.throttle > 0:
                        dt = time.time() - start
                        if dt < self.throttle:
                            delay = self.throttle - dt
                            if delay < 0.001:
                                corr = dt_corr - self.throttle
                                if corr > 0:
                                    if corr > delay:
                                        time.sleep(0.0000001)
                                    else:
                                        time.sleep(delay - corr)
                                else:
                                    time.sleep(delay)
                            else:
                                time.sleep(delay)
        self.log.debug(f"{self.name} terminating send_worker")
        return

    def inbound_init(self):
        """This function can optionally be overriden for init-purposes, needs to return True to start inbound(), active in 'dual' mode only"""
        return True

    def inbound(self):
        """This function is overriden by the implementation: it acquires an object, active in 'dual' mode only"""
        self.log.error(f"Process {self.name} doesn't override inbound function!")
        time.sleep(1)
        return None

    def receive_worker(self):
        self.log.debug(f"{self.name} started receive_worker")
        outbound_active = self.outbound_init()
        while self.bActive is True:
            if self.transport == "zmq":
                try:
                    msg = self.zmq_send_socket.recv()
                except zmq.error.Again:
                    msg = None
                    ev = None
                    if self.zmq_send_socket.closed is True:
                        self.log.info("{self.name} ZMQ thread terminated")
                        self.zmq_send_socket.close()
                        exit(0)
                if msg is not None:
                    ev = IndraEvent.from_json(msg)
                else:
                    ev = None
            else:
                try:
                    ev = self.send_queue.get(timeout=0.1)
                except queue.Empty:
                    ev = None
            if ev is not None:
                self.log.debug(f"Received: {ev.domain}")
                if ev.domain == "$cmd/quit":
                    self.shutdown()
                    self.log.debug(f"{self.name} terminating receive_worker...")
                    self.bActive = False
                    self.log.info(f"Terminating process {self.name}")
                    exit(0)
                else:
                    if outbound_active is True:
                        self.outbound(ev)
                    else:
                        self.log.warning(
                            f"Ignoring cmd, inactive: {ev.domain} from {ev.from_id}"
                        )
        self.log.debug(f"{self.name} termination of receive_worker")
        return

    def outbound_init(self):
        """This function can optionally be overriden for init-purposes, needs to return True to start outbound()"""
        return True

    def outbound(self, ev: IndraEvent):
        """This function receives an IndraEvent object that is to be transmitted outbound"""
        self.log.error(f"Process {self.name} doesn't override outbound function!")

    def async_rt_worker(self):
        asyncio.run(self.in_out_bound())

    async def in_out_bound(self):
        bActive = True
        self.log.info("Async handler started")
        await self.async_init()
        while bActive:
            if self.send_queue.empty() is False:
                ev = self.send_queue.get()
                if ev.domain == "$cmd/quit":
                    await self.async_shutdown()
                    self.log.info("Terminating async handler")
                    return
                else:
                    await self.async_outbound(ev)
            else:
                await asyncio.sleep(0.05)

    async def async_shutdown(self):
        """This function is called in async mode just before shutdown"""
        pass

    async def async_outbound(self):
        """This function receives an IndraEvent object in async mode that is to be transmitted outbound"""
        self.log.error(f"Process {self.name} doesn't override async_outbound function!")

    def shutdown(self):
        """This function is called just before shutdown"""
        pass

    def subscribe(self, domains):
        """Subscribe to domain"""
        if domains is None or domains == "":
            self.log.error("Please provide a valid domain(s)!")
            return False
        ie = IndraEvent()
        ie.domain = "$cmd/subs"
        ie.from_id = self.name
        ie.data_type = "vector/string"
        if isinstance(domains, list) is True:
            ie.data = json.dumps(domains)
        else:
            ie.data = json.dumps([domains])
        self.event_send(ie)
        return True

    def unsubscribe(self, domains):
        """Unsubscribe from domain"""
        if domains is None or domains == "":
            self.log.error("Please provide a valid domain(s)!")
            return False
        ie = IndraEvent()
        ie.domain = "$cmd/unsubs"
        ie.from_id = self.name
        ie.data_type = "vector/string"
        if isinstance(domains, list) is True:
            ie.data = json.dumps(domains)
        else:
            ie.data = json.dumps([domains])
        self.event_send(ie)
        return True
