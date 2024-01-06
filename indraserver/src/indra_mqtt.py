import paho.mqtt.client as mq

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
        super().__init__(event_queue, send_queue, config_data, signal_handler=False)
        self.set_throttle(1)

        self.mqtt_server = config_data["mqtt_server"]
        self.mqtt_port = config_data["mqtt_port"]
        self.mqtt_keepalive = config_data["mqtt_keepalive"]
        self.mqtt_subs = config_data["mqtt_subscriptions"]
        self.outbound_prefix = config_data["outbound_prefix"]

        self.bConnectActive = False

    def on_connect(self, client, userdata, flags, rc):
        self.log.info(f"MQTT connection established to {self.mqtt_server}")
        self.bConnectActive = True
        for sub in self.mqtt_subs:
            self.mq_client.subscribe((sub, 0))

    def on_message(self, client, userdata, msg):
        self.log.debug(f"MQTT message received: {msg.topic}, {msg.payload}")
        ev = IndraEvent()
        ev.domain = "mqtt/" + msg.topic
        ev.from_id = self.name
        ev.data = msg.payload
        self.event_queue.put(ev)

    def inbound_init(self):
        self.mq_client = mq.Client()
        self.mq_client.on_connect = self.on_connect
        self.mq_client.on_message = self.on_message
        self.mq_client.connect(
            self.mqtt_server, self.mqtt_port, self.mqtt_keepalive
        )
        return True

    def inbound(self):
        # self.mq_client.loop_forever()
        self.mq_client.loop(timeout=0.5)
        return None

    def outbound(self, ev: IndraEvent):
        if self.bConnectActive is True:
            topic = self.outbound_prefix + '/' + ev.domain
            msg = ev.data
            self.mq_client.publish(topic = topic, payload = msg )
        else:
            self.log.warning(f"Publish-request from {ev.from_id}, {ev.domain}, MQTT connection not established!")

    def shutdown(self):
        if self.bConnectActive is True:
            self.mq_client.disconnect()
            self.log.info("MQTT connection closed")
