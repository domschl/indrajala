import logging
import threading
import time
from queue import Queue

from indralib.indra_event import IndraEvent


class IndraModule:
    def __init__(
        self,
        name: str,
        central_queue: Queue,
        module_destination_queue: Queue,
        config_data,
        poll_delay=0.05,
    ):
        self.name = name
        self.log = logging.getLogger(name)
        self.central_queue = central_queue
        self.module_destination_queue = module_destination_queue
        self.config = config_data
        self.poll_delay = poll_delay
        try:
            self.loglevel = self.config["loglevel"].upper()
            self.log.setLevel(self.loglevel)
        except Exception as e:
            self.loglevel = logging.INFO
            self.log.setLevel(self.loglevel)
            self.log.error(
                f"Missing entry 'loglevel' in module config for {self.name}: {e}"
            )

        self.receiver_worker_thread_handle = threading.Thread(
            target=self.receiver_worker_thread, args=(), daemon=True
        )
        self.receiver_worker_thread_handle.start()
        self.sender_worker_thread_handle = threading.Thread(
            target=self.sender_worker_thread, args=(), daemon=True
        )
        self.sender_worker_thread_handle.start()
        self.active = True

    def receiver_worker_thread(self):
        while self.active is True:
            rec_msg: IndraEvent = self.receive_message()
            if rec_msg is not None:
                self.central_queue.put(rec_msg)
            else:
                time.sleep(self.poll_delay)
        self.log.info(f"Worker thread {self.name} terminating")

    def sender_worker_thread(self):
        while self.active is True:
            msg: IndraEvent = self.module_destination_queue.get()
            self.module_destination_queue.task_done()
            if msg.domain == "$cmd/quit":
                self.active = False
            else:
                self.send_message(msg)
        self.log.info(f"Worker thread {self.name} terminating")

    def send_message(self, msg: IndraEvent):
        return None

    def receive_message(self) -> IndraEvent:
        return None


class TestModule(IndraModule):
    def __init__(
        self,
        name: str,
        central_queue: Queue,
        module_destination_queue: Queue,
        config_data,
        poll_delay=0.05,
    ):
        super().__init__(
            name, central_queue, module_destination_queue, config_data, poll_delay
        )

    def send_message(self, msg: IndraEvent):
        print(msg.domain)
        return None

    def receive_message(self) -> IndraEvent:
        a = IndraEvent()
        a.domain = "test"
        return a
