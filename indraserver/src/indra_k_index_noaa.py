import time
import threading
from datetime import datetime
import zoneinfo
import json
import urllib.request
import yaml
import os

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
        self.config_data = config_data
        self.bConnectActive = True

        if "run_condition" in config_data and config_data["run_condition"] != "default":
            self.run_condition = config_data["run_condition"]
            self.log.warning(f"Using custom run_condition {self.run_condition}")
        else:
            self.run_condition = f"periodic@20m"
        if (
            "abort_error_count" in config_data
            and config_data["abort_error_count"] != "default"
        ):
            self.abort_error_count = config_data["abort_error_count"]
        else:
            self.abort_error_count = 5
        if (
            "timer_resolution_sec" in config_data
            and config_data["timer_resolution_sec"] != "default"
        ):
            self.resolution_sec = config_data["timer_resolution_sec"]
        else:
            self.resolution_sec = 1.0
        self.descriptors = {
            "k_index": "NOAA: The K-index, and by extension the Planetary K-index, are used to characterize the magnitude of geomagnetic storms. Kp is an excellent indicator of disturbances in the Earth's magnetic field and is used by SWPC to decide whether geomagnetic alerts and warnings need to be issued for users who are affected by these disturbances. The principal users affected by geomagnetic storms are the electrical power grid, spacecraft operations, users of radio signals that reflect off of or pass through the ionosphere, and observers of the aurora.",
        }
        # https://www.swpc.noaa.gov/products/planetary-k-index
        self.meass = {
            "k_index": ("planetary_k_index", "number/float/geomagnetic/k_index"),
        }
        o_context = "geomagnetic_storm"
        o_location = "earth"
        k = "k_index"
        self.domain = f"$event/measurement/{self.meass[k][0]}/{o_context}/{o_location}"
        self.last_event_time = None
        self.last_event_time_init = False
        self.last_event_inbound_init = False
        self.last_event_uuid4 = self.get_last_event(self.domain)

    def get_data(self):
        # self.log.info(self.url_latest)
        if self.last_event_time_init is False:
            self.log.error(
                "Job started before last_event_time_init, can lead to duplicated events"
            )
            return False
        url_k_index = "https://services.swpc.noaa.gov/json/boulder_k_index_1m.json"
        self.log.info(f"Reading {url_k_index}")
        try:
            with urllib.request.urlopen(url_k_index) as url:
                data = json.loads(url.read().decode())
        except Exception as e:
            self.log.error(f"Cannot read {self.url_latest}: {e}")
            return False
        upd = 0
        for d in data:
            utc_iso = d["time_tag"] + ".000"
            jd = IndraTime.ISO2julian(utc_iso)
            dt = IndraTime.julian2datetime(jd)
            if self.last_event_time is not None and dt <= self.last_event_time:
                continue
            ie = IndraEvent()
            ie.time_jd_start = jd
            ie.time_jd_end = jd
            # f"$event/measurement/{o_measurement}/{o_context}/{o_location}"
            k = "k_index"
            ie.domain = self.domain
            ie.data_type = self.meass[k][1]
            ie.from_id = self.config_data["name"]
            ie.data_type = self.meass[k][1]
            ie.data = json.dumps(float(d["k_index"]))
            self.event_send(ie)
            self.log.debug(f"Sent event {ie.domain} {ie.data_type} {ie.data}")
            upd += 1
            if dt > self.last_event_time:
                self.last_event_time = dt
        self.log.info(f"Sent {upd} events")
        return True

    def _start_job(self):
        ret = self.create_timer_thread(
            self.name,
            self.run_condition,
            self.get_data,
            resolution_sec=self.resolution_sec,
            abort_error_count=self.abort_error_count,
        )
        return ret

    def inbound_init(self):
        if not self.bConnectActive:
            return False
        self.last_event_inbound_init = True
        if self.last_event_time_init is True:
            return self._start_job()
        return True

    def inbound(self):
        time.sleep(1)
        return None

    def outbound(self, ev: IndraEvent):
        if ev.uuid4 == self.last_event_uuid4:
            if ev.data_type != "json/indraevent":
                self.last_event_time = None
            else:
                last_event = json.loads(ev.data)
                self.last_event_time = IndraTime.julian2datetime(
                    last_event["time_jd_start"]
                )
            self.last_event_time_init = True
            if self.last_event_inbound_init is True:
                self._start_job()
            return
        self.log.warning(
            f"Publish-request from {ev.from_id}, {ev.domain} to scheduled_downloader"
        )

    def shutdown(self):
        self.thread_active = False
