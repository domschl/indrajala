# import logging
# import os
import time
# import signal
# import atexit
# from datetime import datetime
# from zoneinfo import ZoneInfo
# import multiprocessing as mp
# import threading

import paho.mqtt.client as mq

# XXX dev only
import sys
import os
path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "indralib/src"
)
sys.path.append(path)
from indra_event import IndraEvent  # type: ignore

from indra_serverlib import IndraProcessCore

class IndraProcess(IndraProcessCore):
    def __init__(self, event_queue, send_queue, config_data):
        super().__init__(event_queue, send_queue, config_data, False)
        # self.subscribe("pingpong/#")
        self.set_throttle(1)
        
        self.mqtt_server = config_data['mqtt_server']
        self.mqtt_port = config_data['mqtt_port']
        self.mqtt_keepalive = config_data['mqtt_keepalive']
        self.mqtt_subs = config_data['mqtt_subscriptions']

    def on_connect(self, client, userdata, flags, rc):
        self.log.info("MQTT connection established")
        for sub in self.mqtt_subs:
            self.mq_rcv_client.subscribe((sub, 0))

    def on_message(self, client, userdata, msg):
        self.log.info(f"MQTT message received: {msg.topic}, {msg.payload}")
        ev = IndraEvent()
        ev.domain = "mqtt/"+msg.topic
        ev.from_id = self.name
        ev.data = msg.payload
        self.event_queue.put(ev)

    def inbound_init(self):
        self.mq_rcv_client = mq.Client()
        self.mq_rcv_client.on_connect = self.on_connect
        self.mq_rcv_client.on_message = self.on_message
        self.mq_rcv_client.connect(self.mqtt_server, self.mqtt_port, self.mqtt_keepalive)

    def inbound(self):
        # self.mq_client.loop_forever()
        self.mq_rcv_client.loop(timeout=0.5)
        return None
    
    def outbound(self, ev:IndraEvent):
        self.log.info(f"Got a PingPong: {ev.domain}, sent by {ev.from_id}")
