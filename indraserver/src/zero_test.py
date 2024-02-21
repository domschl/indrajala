import json
import time

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
        self.n = 0
        self.set_throttle(1.0 / config_data["ping_frequency_hz"])
        self.log.info(
            f"Starting ZMQ-PingPong, message frequency: {config_data['ping_frequency_hz']}"
        )  #  with config: {config_data}")

    def inbound(self):
        self.n = self.n + 1
        # self.log.info(f"Z-Padam! {self.n}")
        ev = IndraEvent()
        ev.from_id = self.name
        ev.domain = f"zero_test/{self.name}/{self.n}"
        return ev

    def outbound(self, ev: IndraEvent):
        self.log.debug(f"Got a ZMQ-PingPong: {ev.domain}, sent by {ev.from_id}")

    def run(self):
        self.launcher()


if __name__ == "__main__":
    # print("Starting zero_test.py")
    if len(sys.argv) != 3:
        print("Usage: zero_test.py <main_process_zeromq_port> <json_config_string>")
        sys.exit(1)
    port = int(sys.argv[1])
    try:
        if sys.argv[2][0] == "'" and sys.argv[2][-1] == "'":
            config = json.loads(sys.argv[2][1:-1])
        else:
            config = json.loads(sys.argv[2])
    except Exception as e:
        print("JSON Error: ", e)
        sys.exit(1)

    ipc = IndraProcess(config, "zmq", None, None, port, config["zeromq_port"])
    ipc.run()
