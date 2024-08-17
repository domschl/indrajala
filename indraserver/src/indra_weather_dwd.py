import time
import json
from datetime import datetime
from urllib.request import urlopen
from io import StringIO, BytesIO
from zipfile import ZipFile
import xml.etree.cElementTree as et

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
        self.url_station_forecast_template = "https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/single_stations/{0}/kml/MOSMIX_L_LATEST_{0}.kmz"
        if "station_id" in config_data:
            self.station_id = config_data["station_id"]
            self.url_station_forecast = self.url_station_forecast_template.format(
                self.station_id
            )
        else:
            self.log.error(
                "No station_id in config_data"
            )
            self.station_id = None
            self.url_station_forecast = None
        if "run_condition" in config_data and config_data["run_condition"] != "default":
            self.run_condition = config_data["run_condition"]
            self.log.warning(f"Using custom run_condition {self.run_condition}")
        else:
            self.run_condition = "hourly@:07"
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

    def _xml_parser(self, child):
        t = child.tag.split('}')
        if len(t)==2:
            tag = t[1]
        else:
            tag =""
        attribs = {}
        for a in child.attrib.keys():
            at = a.split('}')
            if len(at) == 2:
                attrib = at[1]
            else:
                attrib = at
            attribs[attrib] = child.attrib[a]
        if child.text is None:
            text = ""
        else:
            text = child.text
        return tag, attribs, text

    def _xml_analyse(self, xmlroot):
        fc = {}
        fc['timesteps'] = []
        for child in xmlroot:
            tag, attrib, text = self._xml_parser(child)
            for child2 in child:
                tag, attrib, text = self._xml_parser(child2)
                for child3 in child2:
                    tag, attrib, text = self._xml_parser(child3)
                    for child4 in child3:
                        tag, attrib, text = self._xml_parser(child4)
                        if tag == "ForecastTimeSteps":
                            mode = "time"
                            param = ""
                        elif tag == 'Forecast' and 'elementName' in attrib:
                            mode = 'forecast'
                            param = attrib['elementName']
                        else:
                            mode = ""
                            param = ""
                        for child5 in child4:
                            tag, attrib, text = self._xml_parser(child5)
                            if mode == "time" and tag == "TimeStep":
                                fc['timesteps'].append(text)
                            elif mode == 'forecast' and tag == 'value':
                                fc[param] = text.split()
        return fc

# fc dict_keys(['timesteps', 'PPPP', 'E_PPP', 'TX', 'TTT', 'E_TTT', 'Td', 'E_Td', 
# 'TN', 'TG', 'TM', 'T5cm', 'DD', 'E_DD', 'FF', 'E_FF', 'FX1', 'FX3', 'FX625', 
# 'FX640', 'FX655', 'FXh', 'FXh25', 'FXh40', 'FXh55', 'N', 'Neff', 'Nlm', 
# 'Nh', 'Nm', 'Nl', 'N05', 'VV', 'VV10', 'wwM', 'wwM6', 'wwMh', 'wwMd', 'ww', 
# 'ww3', 'W1W2', 'wwP', 'wwP6', 'wwPh', 'wwPd', 'wwZ', 'wwZ6', 'wwZh', 'wwD', 
# 'wwD6', 'wwDh', 'wwC', 'wwC6', 'wwCh', 'wwT', 'wwT6', 'wwTh', 'wwTd', 'wwS', 
# 'wwS6', 'wwSh', 'wwL', 'wwL6', 'wwLh', 'wwF', 'wwF6', 'wwFh', 'DRR1', 'RR6c', 
# 'RRhc', 'RRdc', 'RR1c', 'RRS1c', 'RRL1c', 'RR3c', 'RRS3c', 'R101', 'R102', 
# 'R103', 'R105', 'R107', 'R110', 'R120', 'R130', 'R150', 'RR1o1', 'RR1w1', 
# 'RR1u1', 'R600', 'R602', 'R610', 'R650', 'Rh00', 'Rh02', 'Rh10', 'Rh50', 
# 'Rd00', 'Rd02', 'Rd10', 'Rd50', 'SunD', 'RSunD', 'PSd00', 'PSd30', 'PSd60', 
# 'RRad1', 'Rad1h', 'SunD1', 'SunD3', 'PEvap', 'WPc11', 'WPc31', 'WPc61', 
# 'WPch1', 'WPcd1'])
# Doc on fields:
# https://opendata.dwd.de/weather/lib/MetElementDefinition.xml

    def _xml_dwd_extract(self, fc):
        l = None
        dwd_fc = {}
        for k in fc.keys():
            if l is None:
                l = len(fc[k])
            else:
                if len(fc[k]) != l:
                    print(f"Bad len: {k}")
                    return None
            if k == 'timesteps':
                dwd_fc['time'] = [datetime.fromisoformat(ti) for ti in fc['timesteps']]
            elif k == 'TTT':
                dwd_fc['temperature'] = [ float(ti) - 273.15 for ti in fc['TTT']]
                
        return dwd_fc            

    def get_data(self):
        try:
            self.log.debug(f'Downloading: {self.url_station_forecast}')
            resp = urlopen(self.url_station_forecast)
            zfile = ZipFile(BytesIO(resp.read()))
            iodata = zfile.open(
                zfile.namelist()[0]).read()
        except Exception as e:
            self.log.error(f'Unable to download {self.url_station_forecast}: {e}')
            return None
        xmlroot = et.fromstring(iodata)
        fc = self._xml_analyse(xmlroot)
        dwd_fc = self._xml_dwd_extract(fc)
        vals = [("temperature", "vector/tuple/jd/float/temperature/celsius")]
        for val in vals:
            if val[0] not in dwd_fc:
                self.log.error(f"Value {val[0]} not in forecast")
                continue
            ie = IndraEvent()
            ie.time_jd_start = IndraTime.ISO2julian(fc['timesteps'][0])
            ie.time_jd_end = IndraTime.ISO2julian(fc['timesteps'][-1])
            ie.domain = f"$event/forecast/{val[0]}/dwd/{self.station_id}"
            ie.data_type = f"{val[1]}"
            ie.from_id = self.name
            data = [(jd, y) for jd, y in zip(dwd_fc['time'], dwd_fc[val[0]])]
            ie.data = json.dumps(data)
            self.event_send(ie)

    def inbound_init(self):
        if not self.bConnectActive or self.station_id is None:
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
