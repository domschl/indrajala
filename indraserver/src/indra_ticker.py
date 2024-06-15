import time
import threading

from indralib.indra_event import IndraEvent
from indralib.indra_time import IndraTime

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
            mode="dual",
        )
        self.bConnectActive = True
        self.mand_fields = ["active", "name", "params", "source", "interval_sec"]
        self.tasks = config_data["task"]
        for task in self.tasks:
            valid = True
            for field in self.mand_fields:
                if field not in task:
                    self.log.error(f"Missing field {field} in task {task}")
                    task["active"] = False
                    valid = False
            if not valid:
                continue
            if not task["active"]:
                self.log.debug(f"Task {task["name"]} is not active")
                continue
            src = task["source"].split(".")
            if len(src) != 2:
                self.log.error(f"Invalid source {task["source"]} in task {task["name"]}")
                task["active"] = False
                continue
            try:
                module = __import__(src[0])
                task["entry"] = getattr(module, src[1])
            except Exception as e:
                self.log.error(f"Could not import source {task["source"]} in task {task["name"]}: {e}")
                task["active"] = False
                continue
            task["params"]["name"] = f"{self.name}/{task["name"]}"

    def ticker(self):
        self.log.info("Ticker thread started")
        for task in self.tasks:
            task['last_run'] = time.time()
        while self.thread_active:
            for task in self.tasks:
                if not task["active"]:
                    continue
                if time.time() - task["last_run"] < task["interval_sec"]:
                    continue
                task["last_run"] = time.time()
                self.log.info(f"Running task {task["name"]}")
                state = task["entry"](self.log, task["params"], self.event_send)
                if state is False:
                    self.log.error(f"Task {task["name"]} failed, deactivating")
                    task["active"] = False
            time.sleep(1)
        self.log.info("Ticker thread stopped")

    def get_finance_data(self, task):
        self.log.info(f"Getting finance data for {task["name"]}")

    def get_news_data(self, task):
        self.log.info(f"Getting news data for {task["name"]}")

    def get_weather_data(self, task):
        self.log.info(f"Getting weather data for {task["name"]}")
            
    def inbound_init(self):
        # start thread
        self.thread_active = True
        self.ticker_thread = threading.Thread(target=self.ticker, daemon=True)
        self.ticker_thread.start()
        return True

    def inbound(self):
        time.sleep(1)
        return None

    def outbound(self, ev: IndraEvent):
        self.log.warning(f"Publish-request from {ev.from_id}, {ev.domain} to Ticker")

    def shutdown(self):
        self.thread_active = False
