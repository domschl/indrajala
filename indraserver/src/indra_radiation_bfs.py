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
        self.url_latest_template = "https://www.imis.bfs.de/ogc/opendata/ows?service=WFS&version=1.1.0&request=GetFeature&typeName=opendata:odlinfo_odl_1h_latest&outputFormat=application/json&viewparams=kenn:{kenn}&maxFeatures=1"
        if "bfs_kenn" in config_data:
            self.kenn = config_data["bfs_kenn"]
            self.url_latest = self.url_latest_template.format(kenn=self.kenn)
        else:
            self.log.error(
                "No bfs_kenn in config_data, visit https://odlinfo.bfs.de/ODL/DE/service/datenschnittstelle/datenschnittstelle_node.html"
            )
            self.kenn = None
            self.url_latest = None
        # Start scheduled_downloader thread
        self.thread_active = False
        self.last_run = 0

    def get_data(self):
        if self.kenn is not None:
            try:
                with urllib.request.urlopen(self.url_latest) as url:
                    data = json.loads(url.read().decode())
                    self.log.info(data)
                    return True
            except Exception as e:
                self.log.error(f"Cannot read {self.url_latest}: {e}")
                return False
        else:
            self.log.error("No bfs_kenn in config_data")
            return False

    def scheduled_downloader(self):
        self.log.info("scheduled_downloader thread started")
        while self.thread_active:
            tc = time.time()
            if tc % 3600 > 1800 and tc - self.last_run > self.period_sec - 100:
                self.log.info("Getting data")
                self.get_data()
                self.last_run = time.time()
            time.sleep(1)
            self.log.info(f"x{tc % 3600 - 1800} seconds")
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
