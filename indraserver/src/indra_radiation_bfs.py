import time
import json
import urllib.request

from indralib.indra_event import IndraEvent  # type: ignore
from indralib.indra_time import IndraTime  # type: ignore

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
        self.url_latest = "https://www.imis.bfs.de/ogc/opendata/ows?service=WFS&version=1.1.0&request=GetFeature&typeName=opendata:odlinfo_odl_1h_latest&outputFormat=application/json"
        if "bfs_kenn" in config_data:
            self.kenn = config_data["bfs_kenn"]
        else:
            self.log.error(
                "No bfs_kenn in config_data, visit https://odlinfo.bfs.de/ODL/DE/service/datenschnittstelle/datenschnittstelle_node.html"
            )
            self.kenn = None
            self.url_latest = None
        if "run_condition" in config_data and config_data["run_condition"] != "default":
            self.run_condition = config_data["run_condition"]
            self.log.warning(f"Using custom run_condition {self.run_condition}")
        else:
            self.run_condition = "hourly@:30"
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

    def get_data(self):
        # self.log.info(self.url_latest)
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
                        ie.time_jd_start = IndraTime.ISO_to_julian(start_measure)
                        ie.time_jd_end = IndraTime.ISO_to_julian(end_measure)
                        # f"$event/measurement/{o_measurement}/{o_context}/{o_location}"
                        if k in meass:
                            ie.domain = f"$event/measurement/{meass[k][0]}/{o_context}/{o_location}"
                            ie.data_type = meass[k][1]
                            ie.from_id = self.config_data["name"]
                            ie.data_type = meass[k][1]
                            ie.data = json.dumps(float(data[k]))
                            self.event_send(ie)
                            self.log.debug(
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

    def inbound_init(self):
        if not self.bConnectActive or self.kenn is None:
            return False
        ret = self.create_timer_thread(
            self.name,
            self.run_condition,
            self.get_data,
            resolution_sec=self.resolution_sec,
            abort_error_count=self.abort_error_count,
        )
        return ret

    def inbound(self):
        time.sleep(1)
        return None

    def outbound(self, ev: IndraEvent):
        self.log.warning(
            f"Publish-request from {ev.from_id}, {ev.domain} to scheduled_downloader"
        )

    def shutdown(self):
        self.thread_active = False
