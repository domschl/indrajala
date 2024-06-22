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

# https://odlinfo.bfs.de/ODL/DE/service/datenschnittstelle/datenschnittstelle_node.html

# https://www.imis.bfs.de/ogc/opendata/ows?service=WFS&version=1.1.0&request=GetFeature&typeName=opendata:odlinfo_timeseries_odl_1h&outputFormat=application/json&viewparams=kenn:091620001
# https://www.imis.bfs.de/ogc/opendata/ows?service=WFS&version=1.1.0&request=GetFeature&typeName=opendata:odlinfo_odl_1h_latest&outputFormat=application/json
# https://www.imis.bfs.de/ogc/opendata/ows?service=WFS&version=1.1.0&request=GetFeature&typeName=opendata:odlinfo_timeseries_odl_1h&outputFormat=application/json&viewparams=kenn:091620001&maxFeatures=2&sortBy=end_measure+D
# https://www.imis.bfs.de/ogc/opendata/ows?service=WFS&version=1.1.0&request=GetFeature&typeName=opendata:odlinfo_odl_1h_latest&outputFormat=application/json&viewparams=kenn:091620001&maxFeatures=1


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
        if "period_sec" in config_data:
            self.period_sec = config_data["period_sec"]
            if self.period_sec < 3600:
                self.period_sec = 3600
                self.log.warning("Period too short, setting to 1h")
        else:
            self.period_sec = 3600
        self.url_latest = "https://www.imis.bfs.de/ogc/opendata/ows?service=WFS&version=1.1.0&request=GetFeature&typeName=opendata:odlinfo_odl_1h_latest&outputFormat=application/json"
        if "bfs_kenn" in config_data:
            self.kenn = config_data["bfs_kenn"]
        else:
            self.log.error(
                "No bfs_kenn in config_data, visit https://odlinfo.bfs.de/ODL/DE/service/datenschnittstelle/datenschnittstelle_node.html"
            )
            self.kenn = None
            self.url_latest = None
        # Start scheduled_downloader thread
        self.thread_active = False
        self.last_run = 0
        # Testcode
        # self.get_data()

    def get_data(self):
        self.log.info(self.url_latest)
        meass = {
            "radiation": ("gamma_radiation", "number/float/radiation/uSv_h"),
            "radiation_cosmic": (
                "cosmic_gamma_radiation",
                "number/float/radiation/uSv_h",
            ),
            "radiation_terrestrial": (
                "terrestrial_gamma_radiation",
                "number/float/radiation/uSv_h",
            ),
        }
        o_context = "radiation"
        o_location = "bfs_muc_neuhausen"

        if self.kenn is not None:
            try:
                with urllib.request.urlopen(self.url_latest) as url:
                    data = json.loads(url.read().decode())
            except Exception as e:
                self.log.error(f"Cannot read {self.url_latest}: {e}")
                return False
            # self.log.info(data)
            for feature in data["features"]:
                props = feature["properties"]
                if props["kenn"] == self.kenn:
                    # self.log.info(props)
                    data = {}
                    data["radiation"] = props["value"]
                    data["radiation_cosmic"] = props["value_cosmic"]
                    data["radiation_terrestrial"] = props["value_terrestrial"]
                    start_measure = props["start_measure"][:-1] + ".000"  # remove Z
                    end_measure = props["end_measure"][:-1] + ".000"
                    for k in data.keys():
                        ie = IndraEvent()
                        ie.time_jd_start = IndraTime.ISO2julian(start_measure)
                        ie.time_jd_end = IndraTime.ISO2julian(end_measure)
                        # f"$event/measurement/{o_measurement}/{o_context}/{o_location}"
                        if k in meass:
                            ie.domain = f"$event/measurement/{meass[k][0]}/{o_context}/{o_location}"
                            ie.data_type = meass[k][1]
                            ie.from_id = self.config_data["name"]
                            ie.data_type = meass[k][1]
                            ie.data = json.dumps(float(data[k]))
                            self.event_send(ie)
                            self.log.info(
                                f"Sent event {ie.domain} {ie.data_type} {ie.data}"
                            )
                        else:
                            self.log.warning(f"Unknown key {k} in data")
                    return True
            self.log.warning(f"No data for kenn {self.kenn}")
            return False
        else:
            self.log.error("No bfs_kenn in config_data")
            return False

    def scheduled_downloader(self):
        self.log.info("scheduled_downloader thread started")
        while self.thread_active:
            tc = time.time()
            tcr = int(tc % 3600)
            if tcr > 1800 and tcr < 1810 and tc - self.last_run > self.period_sec - 100:
                self.log.info("Getting data")
                self.get_data()
                self.last_run = time.time()
            time.sleep(1)
            # self.log.info(f"x{tcr - 1800} seconds")
        self.log.info("scheduled_downloader thread stopped")

    def inbound_init(self):
        if not self.bConnectActive or self.kenn is None:
            return False
        # start thread
        self.thread_active = True
        self.scheduled_downloader_thread = threading.Thread(
            target=self.scheduled_downloader, daemon=True
        )
        self.scheduled_downloader_thread.start()
        return True

    def inbound(self):
        time.sleep(1)
        return None

    def outbound(self, ev: IndraEvent):
        self.log.warning(
            f"Publish-request from {ev.from_id}, {ev.domain} to scheduled_downloader"
        )

    def shutdown(self):
        self.thread_active = False
