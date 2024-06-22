import time
import threading
import pandas as pd
import bs4
import urllib.request
from datetime import datetime
import zoneinfo
import json

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
        if "period_sec" in config_data:
            self.period_sec = config_data["period_sec"]
            if self.period_sec < 3600:
                self.period_sec = 3600
                self.log.warning("Period too short, setting to 1h")
        else:
            self.period_sec = 3600
        # Start scheduled_downloader thread
        self.thread_active = False
        self.last_run = 0

    def scheduled_downloader(self):
        self.log.info("scheduled_downloader thread started")
        while self.thread_active:
            tc = time.time()
            tcr = int(tc % 3600)
            if tcr < 10 and tc - self.last_run > self.period_sec - 100:
                self.log.info("Getting data")
                self.get_data()
                self.last_run = time.time()
            time.sleep(1)
            # self.log.info(f"x-{3600-tcr} seconds")
        self.log.info("scheduled_downloader thread stopped")

    def get_data(self):
        url = "https://www.meteo.physik.uni-muenchen.de/mesomikro/stadt/messung.php"
        meass = {
            "temperature": ("temperature", "number/float/temperature/celsius"),
            "humidity": ("humidity", "number/float/humidity/percentage"),
            "illuminance": ("illuminance", "number/float/illuminance/lux"),
            "pressureNN": ("pressure", "number/float/pressure/hpa"),
            "wind_speed": ("wind_speed", "number/float/wind_speed/m_s"),
            "solar_radiation": ("solar_radiation", "number/float/radiation/w_m2"),
            "diffuse_radiation": ("diffuse_radiation", "number/float/radiation/w_m2"),
            "atmospheric_radiation": (
                "atmospheric_radiation",
                "number/float/radiation/w_m2",
            ),
            "uv_index": ("uv_index", "number/float/uv_index"),
            "pressure": (
                "local_pressure",
                "number/float/localpressure/hpa",
            ),
            "wind_direction": ("wind_direction", "number/float/wind_direction/degree"),
            "precipitation": ("precipitation", "number/float/precipitation/mm"),
        }
        o_context = "climate"
        o_location = "uni_muc"

        try:
            html = urllib.request.urlopen(url).read()
            doc = bs4.BeautifulSoup(html, "html.parser")
            df2 = pd.read_html(html)
        except Exception as e:
            self.log.error(f"Download of data at {url} failed: {e}")
            return False
        if len(df2) != 4:
            self.log.error(f"Invalid number of tables: {len(df2)}")
            return False
        try:
            time_str = doc.text.split("\n")[8].strip()
            dt = datetime.strptime(time_str, "%d.%m.%Y %H:%M").astimezone(
                zoneinfo.ZoneInfo("Europe/Berlin")
            )
        except Exception as e:
            self.log.error(f"Could not parse time {time_str}: {e}")
            return False

        try:
            jd = IndraTime.datetime2julian(dt)
            data = {}
            time_data = {}
            time_data["time"] = dt
            time_data["jd"] = jd
            if df2[0][0][2] == "Lufttemperatur":
                data["temperature"] = df2[0][1][2].split(" ")[0]
            else:
                self.log.warn("Invalid format for table 0, lufttemperatur")
            if df2[0][0][5] == "Relative Feuchte":
                data["humidity"] = df2[0][1][5].split(" ")[0]
            else:
                self.log.warn("Invalid format for table 0, relative feuchte")
            if df2[0][0][6] == "Windgeschwindigkeit":
                data["wind_speed"] = df2[0][2][6].split(" ")[0]
            else:
                self.log.warn("Invalid format for table 0, windgeschwindigkeit")

            if df2[2][0][1] == "Globalstr.":
                data["solar_radiation"] = df2[2][0][2].split(" ")[0]
            else:
                self.log.warn("Invalid format for table 2, globalstrahlung")
            if df2[2][1][1] == "Diffuse Str.":
                data["diffuse_radiation"] = df2[2][1][2].split(" ")[0]
            else:
                self.log.warn("Invalid format for table 2, diffuse strahlung")
            if df2[2][2][1] == "Atm.Gegenstr.":
                data["atmospheric_radiation"] = df2[2][2][2].split(" ")[0]
            else:
                self.log.warn("Invalid format for table 2, atm. gegenstrahlung")
            if df2[2][4][1] == "UV-Index":
                data["uv_index"] = df2[2][4][2].split(" ")[0]
            else:
                self.log.warn("Invalid format for table 2, uv index")

            if df2[3][0][1] == "Luftdruck 515 m":
                data["pressure"] = df2[3][0][2].split(" ")[0]
            else:
                self.log.warn("Invalid format for table 3, luftdruck")
            if df2[3][1][1] == "Luftdruck NN":
                data["pressureNN"] = df2[3][1][2].split(" ")[0]
            else:
                self.log.warn("Invalid format for table 3, luftdruck NN")
            if df2[3][2][1] == "Windrichtung 30 m Höhe":
                data["wind_direction"] = df2[3][2][2].split(" ")[0]
            else:
                self.log.warn("Invalid format for table 3, windrichtung")
            if df2[3][3][1] == "Niederschlag aktuell":
                data["precipitation"] = df2[3][3][2].split(" ")[0]
            else:
                self.log.warn("Invalid format for table 3, niederschlag")
        except Exception as e:
            self.log.error(f"Could not parse data: {e}")
            return False

        for k in data.keys():
            ie = IndraEvent()
            ie.time_jd_start = jd
            # f"$event/measurement/{o_measurement}/{o_context}/{o_location}"
            if k in meass:
                ie.domain = f"$event/measurement/{meass[k][0]}/{o_context}/{o_location}"
                ie.data_type = meass[k][1]
                ie.from_id = self.config_data["name"]
                ie.data_type = meass[k][1]
                ie.data = json.dumps(float(data[k]))
                self.event_send(ie)
                self.log.debug(f"Sent event {ie.domain} {ie.data_type} {ie.data}")
            else:
                self.log.debug(f"Unknown key {k} in data")
        return True

    def inbound_init(self):
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
