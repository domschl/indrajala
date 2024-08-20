import paho.mqtt.client as mq
import json

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
            mode="dual",
        )
        self.set_throttle(1)

        self.mqtt_server = config_data["mqtt_server"]
        self.mqtt_port = config_data["mqtt_port"]
        self.mqtt_keepalive = config_data["mqtt_keepalive"]
        self.raw_mqtt_subscriptions = config_data["raw_mqtt_subscriptions"]
        self.outbound_prefix = config_data["outbound_prefix"]
        parsers = config_data["inbound_parsers"]
        self.inbound_parsers = {}
        # XXX: import externaly defined parsers at some point
        for pars in parsers:
            if len(pars) != 2:
                self.log.error(
                    f'Invalid inbound parser description, required length is 2: "[mqtt-wildcard, parser-name], got len={len(pars)}: {pars}'
                )
                continue
            else:
                m_op = getattr(self, pars[1], None)
                if callable(m_op) is False:
                    self.log.error(
                        f"Inbound parser method {pars[1]} is not known, {pars} is invalid"
                    )
                    continue
                else:
                    self.inbound_parsers[pars[0]] = m_op
                    self.log.info(f"Added inbound parser {pars[0]} -> {pars[1]}")
        parsers = config_data["outbound_parsers"]
        self.outbound_parsers = {}
        for pars in parsers:
            if len(pars) != 2:
                self.log.error(
                    f'Invalid outbound parser description, required length is 2: "[mqtt-wildcard, parser-name], got len={len(pars)}: {pars}'
                )
                continue
            else:
                m_op = getattr(self, pars[1], None)
                if callable(m_op) is False:
                    self.log.error(
                        f"Outbound parser method {pars[1]} is not known, {pars} is invalid"
                    )
                    continue
                else:
                    self.outbound_parsers[pars[0]] = pars[1]
                    self.log.info(f"Added outbound parser {pars[0]} -> {pars[1]}")

        self.bConnectActive = False

    def on_connect(self, client, userdata, flags, rc):
        self.log.info(f"MQTT connection established to {self.mqtt_server}")
        self.bConnectActive = True
        for sub in self.raw_mqtt_subscriptions:
            self.mq_client.subscribe((sub, 0))
        for sub in self.inbound_parsers:
            if sub not in self.raw_mqtt_subscriptions:
                self.mq_client.subscribe((sub, 0))

    def on_message(self, client, userdata, msg):
        self.log.debug(f"MQTT message received: {msg.topic}, {msg.payload}")
        for sub in self.raw_mqtt_subscriptions:
            if IndraEvent.mqcmp(msg.topic, sub) is True:
                ev = IndraEvent()
                ev.domain = "mqtt/" + msg.topic
                ev.from_id = self.name
                ev.data = msg.payload
                self.event_send(ev)
        for sub in self.inbound_parsers:
            if IndraEvent.mqcmp(msg.topic, sub) is True:
                self.inbound_parsers[sub](msg.topic, msg.payload)

    def inbound_init(self):
        self.mq_client = mq.Client(mq.CallbackAPIVersion.VERSION1)
        self.mq_client.on_connect = self.on_connect
        self.mq_client.on_message = self.on_message
        self.mq_client.connect(self.mqtt_server, self.mqtt_port, self.mqtt_keepalive)
        return True

    def inbound(self):
        # self.mq_client.loop_forever()
        self.mq_client.loop(timeout=0.5)
        return None

    def outbound(self, ev: IndraEvent):
        if self.bConnectActive is True:
            topic = self.outbound_prefix + "/" + ev.domain
            msg = ev.data
            self.mq_client.publish(topic=topic, payload=msg)
        else:
            self.log.warning(
                f"Publish-request from {ev.from_id}, {ev.domain}, MQTT connection not established!"
            )

    def shutdown(self):
        if self.bConnectActive is True:
            self.mq_client.disconnect()
            self.log.info("MQTT connection closed")

    def muwerk(self, topic, message):
        cont_locs = {
            "omu/enviro-master/#": {"location": "home_balkon_env",
                                    "measurements": {
                                        "temperature": ("temperature", "number/float/temperature/celsius", "climate"),
                                        "humidity": ("humidity", "number/float/humidity/percentage", "climate"),
                                        "illuminance": ("illuminance", "number/float/illuminance/lux", "radiation"),
                                        "pressureNN": ("pressure", "number/float/pressure/hpa", "climate"),
                                        "gamma1minavg": ("gamma_radiation_1min_avg", "number/float/radiation/gamma/1minavg", "radiation"),
                                        "gamma10minavg": ("gamma_radiation_10min_avt", "number/float/radiation/gamma/10minavg", "radiation"),
                                        "frequency": ("geiger_radiation", "number/float/frequency/hz", "radiation"),
                                        "unitrain": ("rain", "number/float/rain/unit", "climate"),
                                    }},
            }
        self.log.debug(f"inbound-parser-muwerk: {topic}, {message}")
        if IndraEvent.mqcmp(topic, "omu/+/+/sensor/+"):
            self.log.debug(f"Checking sensor: {topic}, {message}")
            ti = topic.split("/")
            if len(ti) != 5:
                self.log.error(f"Internal parser assumption failure on {topic}")
                return
            device = ti[1]
            sensor = ti[2]
            measurement = ti[4]
            o_context = None
            o_location = None
            o_measurement = None
            o_data_type = None
            found = False
            for cl in cont_locs:
                if IndraEvent.mqcmp(topic, cl):
                    o_location = cont_locs[cl]["location"]
                    if measurement in cont_locs[cl]["measurements"]:
                        o_measurement, o_data_type, o_context = cont_locs[cl]["measurements"][measurement]
                        found = True
                        break
                    break
            if found is True:
                ev = IndraEvent()
                ev.domain = f"$event/measurement/{o_measurement}/{o_context}/{o_location}"
                ev.from_id = f"{self.name}/{topic}"
                ev.data_type = o_data_type
                ev.to_scope = "world"
                try:
                    ev.data = json.dumps(float(message))
                except Exception as e:
                    self.log.warning(f"Failed to convert data {message} for {topic}")
                    return
                self.log.debug(f"Importing {ev.domain}, {ev.data_type}, {ev.data}")
                self.event_send(ev)
            else:
                self.log.debug(f"Not found: {message}, {topic}")

    def ha(self, topic, message):
        self.log.debug(f"inbound-parser-ha: {topic}, {message}")
        topic_list = [
            ("hastates/sensor/klima_balkon_actual_temperature/state", "temperature", "climate", "home_balkon_ha", "number/float/temperature/celsius"),
            ("hastates/sensor/klima_balkon_humidity/state", "humidity", "climate", "home_balkon_ha", "number/float/humidity/percentage"),
            ("hastates/sensor/klima_nordseite_temperature/state", "temperature", "climate", "home_nordseite_ha", "number/float/temperature/celsius"),
            ("hastates/sensor/klima_nordseite_humidity/state", "humidity", "climate", "home_nordseite_ha", "number/float/humidity/percentage"),
        ]
        for topic_i in topic_list:
            if IndraEvent.mqcmp(topic, topic_i[0]) is True:
                ev = IndraEvent()
                ev.domain = f"$event/measurement/{topic_i[1]}/{topic_i[2]}/{topic_i[3]}"
                ev.from_id = f"{self.name}/{topic_i[0]}"
                ev.data_type = topic_i[4]
                ev.to_scope = "world"
                try:
                    ev.data = json.dumps(float(message))
                except Exception as e:
                    self.log.warning(f"Failed to convert data {message} for {topic}")
                    return
                self.log.info(f"Importing {ev.domain}, {ev.data_type}, {ev.data}")
                self.event_send(ev)
