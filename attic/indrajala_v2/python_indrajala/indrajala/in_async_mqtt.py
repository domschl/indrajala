import asyncio
import logging
import queue
import socket
import time
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import paho.mqtt.client as mqtt

# XXX dev only
import sys

path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "indralib/src"
)
sys.path.append(path)
from indra_event import IndraEvent  # type: ignore


class AsyncMqttHelper:
    """Helper module for async wrapper for paho mqtt"""

    def __init__(self, loop, client, loglevel):
        self.log = logging.getLogger("MqttHelper")
        self.log.setLevel(loglevel)
        self.loop = loop
        self.client = client
        self.client.on_socket_open = self.on_socket_open
        self.client.on_socket_close = self.on_socket_close
        self.client.on_socket_register_write = self.on_socket_register_write
        self.client.on_socket_unregister_write = self.on_socket_unregister_write
        self.got_message = None

    def on_socket_open(self, client, userdata, sock):
        def cb():
            client.loop_read()

        self.loop.add_reader(sock, cb)
        self.misc = asyncio.create_task(self.misc_loop(), name="AsyncMqttHelper")

    def on_socket_close(self, client, userdata, sock):
        self.loop.remove_reader(sock)
        self.misc.cancel()

    def on_socket_register_write(self, client, userdata, sock):
        def cb():
            client.loop_write()

        self.loop.add_writer(sock, cb)

    def on_socket_unregister_write(self, client, userdata, sock):
        self.loop.remove_writer(sock)

    async def misc_loop(self):
        state = True
        while state is True:
            if self.client.loop_misc() != mqtt.MQTT_ERR_SUCCESS:
                state = False
            if self.client.loop_read() != mqtt.MQTT_ERR_SUCCESS:
                state = False
            if self.client.loop_write() != mqtt.MQTT_ERR_SUCCESS:
                state = False
            try:
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break


class AsyncMqtt:
    """Async wrapper for paho_mqtt"""

    def __init__(self, loop, mqtt_server, ignore_retained, loglevel, reconnect_delay=1):
        self.log = logging.getLogger("AsyncMqtt")
        self.log.setLevel(loglevel)
        self.loop = loop
        self.mqtt_server = mqtt_server
        self.ignore_retained = ignore_retained
        self.reconnect_delay = reconnect_delay
        self.got_message = None

        self.client_id = hex(uuid.getnode()) + "-" + str(uuid.uuid4())
        self.client = mqtt.Client(client_id=self.client_id)
        self.client.enable_logger(self.log)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        self.ignored = False
        self.aioh = AsyncMqttHelper(self.loop, self.client, loglevel)

        self.que = queue.Queue()

    def last_will(self, last_will_topic, last_will_message, qos=0, retain=True):
        self.client.will_set(last_will_topic, last_will_message, qos, retain)

    async def initial_connect(self, max_wait=30):
        connect_start = time.time()
        connected = False
        while connected is False:
            connected = self.connect()
            if connected is False:
                if time.time() - connect_start < max_wait:
                    self.log.debug("Trying to connect again...")
                    await asyncio.sleep(self.reconnect_delay)
                else:
                    break
        if connected is False:
            self.log.error("Initial connection to MQTT failed, stopping retries.")
        return connected

    def connect(self):
        self.active_disconnect = False
        try:
            self.client.connect(self.mqtt_server, 1883, 45)
            self.client.socket().setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2048)
            self.log.debug("mqtt socket connected.")
            return True
        except Exception as e:
            self.log.debug(f"Connection to {self.mqtt_server} failed: {e}")
            return False

    async def reconnect(self):
        is_connected = False
        while is_connected is False:
            await asyncio.sleep(self.reconnect_delay)
            is_connected = self.connect()

    def on_connect(self, client, userdata, flags, rc):
        self.disconnected = self.loop.create_future()

    def subscribe(self, topic):
        self.client.subscribe(topic)

    def publish(self, topic, payload, retain=False, qos=0):
        self.log.debug(f"PUB: topic: [{topic}] payload: [{payload}]")
        self.client.publish(topic, payload, retain=retain, qos=qos)

    def on_message(self, client, userdata, msg):
        if msg.retain == 1 and self.ignore_retained is True:
            if self.ignored == False:
                self.log.debug("Ignoring received retained messages.")
                self.ignored = True
            return
        self.log.debug(f"Received: {msg.topic} - {msg.payload}")
        if self.got_message is None or self.got_message.done() is True:
            self.log.debug(f"Future unavailable: {msg.topic}, queueing")
            self.que.put((msg.topic, msg.payload, datetime.now(tz=ZoneInfo("UTC"))))
        else:
            self.got_message.set_result(
                (msg.topic, msg.payload, datetime.now(tz=ZoneInfo("UTC")))
            )

    async def message(self):
        if not self.que.empty():
            topic, payload, utctimestamp = self.que.get()
            self.log.debug(f"Unqueuing msg {topic}")
            self.que.task_done()
        else:
            self.got_message = self.loop.create_future()
            topic, payload, utctimestamp = await self.got_message
            self.got_message = None
        return topic, payload, utctimestamp

    def on_disconnect(self, client, userdata, rc):
        self.disconnected.set_result(rc)
        if (
            self.active_disconnect is not True
            and self.reconnect_delay
            and self.reconnect_delay > 0
        ):
            self.log.debug("Trying to reconnect...")
            asyncio.create_task(self.reconnect(), name="MQTT.reconnect")

    async def disconnect(self):
        self.active_disconnect = True
        self.client.disconnect()
        self.log.debug(f"Disconnected: {await self.disconnected}")
        self.active_disconnect = False


class EventProcessor:
    def __init__(self, indra_data, config_data):
        self.log = logging.getLogger("IndraMqtt")
        self.name = config_data["name"]
        try:
            self.loglevel = logging.getLevelName(config_data["loglevel"].upper())
        except Exception as e:
            self.loglevel = logging.DEBUG
            logging.error(
                f"Missing entry 'loglevel' in indrajala.toml section {self.name}: {e}"
            )
        self.log.setLevel(self.loglevel)
        self.config_data = config_data
        self.enabled = False
        self.ignore_retained = self.config_data["ignore_retained"]
        self.first_msg = False
        self.active = True
        return

    def isActive(self):
        return self.active

    async def async_init(self, loop):
        self.loop = loop
        self.async_mqtt = AsyncMqtt(
            loop,
            self.config_data["broker"],
            self.config_data["ignore_retained"],
            self.loglevel,
        )
        if (
            "last_will_topic" in self.config_data
            and "last_will_message" in self.config_data
        ):
            lwt = self.config_data["last_will_topic"]
            lwm = self.config_data["last_will_message"]
            self.async_mqtt.last_will(lwt, lwm)
        await self.async_mqtt.initial_connect()  # Needs to happen after last_will is set.
        for topic in self.config_data["topics"]:
            self.async_mqtt.subscribe(topic)
        self.enabled = True
        return []

    async def get(self):
        if self.enabled is True:
            tp, ms, ut = await self.async_mqtt.message()
            ie = IndraEvent()
            ie.domain = f"$event/{tp}"
            ie.from_id = self.name
            ie.time_jd_start = IndraEvent.datetime2julian(ut)
            ie.data = ms.decode("utf-8")
            return ie

    async def put(self, ie):
        if self.enabled is True:
            self.log.info(f"{self.name}: Received message {ie}")
        return
