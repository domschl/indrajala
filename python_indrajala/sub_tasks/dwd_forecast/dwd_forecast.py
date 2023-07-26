import logging
import os
import sys
import time
import json
import pandas as pd
import xml.etree.cElementTree as et
from urllib.request import urlopen
from datetime import timezone
from io import StringIO, BytesIO
from zipfile import ZipFile
import numpy as np

import asyncio

# XXX temporary hack to import from src
try:
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "../indralib/src"
    )
except:
    path = "~/gith/domschl/indrajala/python_indrajala/indralib/src"
    # expand ~
    path = os.path.expanduser(path)
print(path)
sys.path.append(path)
sys.path.append("/var/lib/indrajala/tasks/indralib/src")

from indra_event import IndraEvent
from indra_client import IndraClient

# Doc on fields:
# https://opendata.dwd.de/weather/lib/MetElementDefinition.xml


class DWD:
    def __init__(self, cache_directory=None, log_handler=None):
        self.log = logging.getLogger("DWD")
        if log_handler is not None:
            self.log.addHandler(log_handler)
        if cache_directory is None:
            self.cachedir = self._get_default_cachedir()
            if self.cachedir is None:
                self.log.error(f"Failed to create cache directory {self.cachedir}")
                self.init = False
                return
        else:
            if os.path.exists(cache_directory) is False:
                try:
                    os.makedirs(cache_directory)
                except Exception as e:
                    self.log.error(
                        f"Failed to create cache directory {cache_directory}: {e}"
                    )
                    self.init = False
                    return
            self.cachedir = cache_directory
        self.forecast_station_url = "https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/single_stations/{0}/kml/MOSMIX_L_LATEST_{0}.kmz"
        self.forecast_max_cache_secs = 3600

    def _get_default_cachedir(self):
        cachedir = "./cache"
        if os.path.exists(cachedir) is False:
            try:
                os.makedirs(cachedir)
            except Exception as e:
                self.log.error(f"Failed to create cache directory {cachedir}: {e}")
                return None
        return "./cache"

    def _filter_tag(self, tag):
        i = tag.find("}")
        if i != -1:
            return tag[i + 1 :]
        else:
            return tag

    def _filter_attrib_dict(self, att):
        d = {}
        for el in att:
            d[self._filter_tag(el)] = att[el]
        return d

    def _download_unpack(self, url):
        try:
            self.log.debug(f"Downloading: {url}")
            resp = urlopen(url)
            zfile = ZipFile(BytesIO(resp.read()))
            iodata = zfile.open(zfile.namelist()[0]).read()
        except Exception as e:
            self.log.error(f"Unable to download {url}: {e}")
            return None
        return iodata

    def _download_forecast_all(self):
        return self._download_unpack(self.forecasts_all_url)

    def _download_station_forecast_raw(self, station_id):
        dl_url = self.forecast_station_url.format(station_id)
        return self._download_unpack(dl_url)

    def station_forecast(self, station_id, force_cache_refresh=False):
        if station_id is None:
            forecast_cache_file = os.path.join(
                self.cachedir, "station-forecast-all.json"
            )
        else:
            forecast_cache_file = os.path.join(
                self.cachedir, f"station-forecast-{station_id}.json"
            )

        dfd = None
        locations = None
        read_station_forecast = False
        if force_cache_refresh is True or os.path.exists(forecast_cache_file) is False:
            read_station_forecast = True
        else:
            try:
                with open(forecast_cache_file, "r") as f:
                    station_forecast = json.load(f)
                if (
                    time.time() - station_forecast["timestamp"]
                    > self.forecast_max_cache_secs
                ):
                    self.log.info(
                        f"Refreshing station forecast, age is > {self.forecast_max_cache_secs}"
                    )
                    read_station_forecast = True
                del station_forecast["timestamp"]
                try:
                    if station_id is None:
                        locations = pd.read_json(json.dumps(station_forecast))
                        self.log.debug(
                            f"Station forecast ALL read from cache {forecast_cache_file}"
                        )
                    else:
                        dfd = pd.read_json(json.dumps(station_forecast))
                        self.log.debug(
                            f"Station forecast {station_id} read from cache {forecast_cache_file}"
                        )
                except Exception as e:
                    self.log.warning(
                        f"Failed to convert station forecast to dataframe: {e}, trying to reload"
                    )
                    read_station_forecast = True
            except Exception as e:
                self.log.error(
                    f"Failed to read station forecast {forecast_cache_file}: {e}"
                )
                read_station_forecast = True

        if read_station_forecast is True:
            if station_id is None:
                iodata = self._download_forecast_all()
            else:
                iodata = self._download_station_forecast_raw(station_id)
            if iodata is None:
                return None
            self.log.debug(f"Starting to parse station {station_id} xml...")
            xmlroot = et.fromstring(iodata)
            self.log.debug("parsed xml")
            timesteps = []
            locations = []
            dfd = None
            for node in xmlroot:
                tag = self._filter_tag(node.tag)
                att = self._filter_attrib_dict(node.attrib)
                location = None
                for node2 in node:
                    tag = self._filter_tag(node2.tag)
                    att = self._filter_attrib_dict(node2.attrib)
                    if tag == "Placemark":
                        location = {}
                        dfd = pd.DataFrame({"time": timesteps})
                        dfd.index = pd.to_datetime(dfd.pop("time"))
                    for node3 in node2:
                        tag = self._filter_tag(node3.tag)
                        att = self._filter_attrib_dict(node3.attrib)
                        for node4 in node3:
                            tag = self._filter_tag(node4.tag)
                            att = self._filter_attrib_dict(node4.attrib)
                            if tag == "Forecast":
                                key = att["elementName"]
                            for node5 in node4:
                                data = None
                                tag = self._filter_tag(node5.tag)
                                att = self._filter_attrib_dict(node5.attrib)
                                text = node5.text
                                if tag == "TimeStep":
                                    timesteps.append(text)
                                    text = None
                                if text is not None:
                                    data = text.split()
                                if data is not None and tag == "value":
                                    dfd[key] = pd.to_numeric(
                                        pd.Series(data, index=dfd.index),
                                        errors="coerce",
                                    )
                                else:
                                    data = None
                # defragment table to avoid performance warnings. Python...
                dfdn = dfd.copy()
                del dfd
                dfd = dfdn
                if location is not None:
                    # Set to UTC:
                    dfd.index = dfd.index.tz_convert(tz="UTC")
                    location["forecast"] = dfd
                    locations.append(location)
                    location = None
            if station_id is not None:
                if len(locations) != 1:
                    self.log.error(
                        "Internal: length of locations is {len(locations)}, expected 1."
                    )
                    return False
                dfd = locations[0]["forecast"]
                try:
                    forecast = json.loads(dfd.to_json())
                    forecast["timestamp"] = time.time()
                except Exception as e:
                    self.log.warning(f"Failed to convert forecast to json: {e}")
                    return dfd
                try:
                    with open(forecast_cache_file, "w") as f:
                        json.dump(forecast, f)
                except Exception as e:
                    self.log.warning(
                        f"Failed to write forecast cache file {forecast_cache_file}: {e}"
                    )
            else:
                try:
                    all_forecasts = {"timestamp": time.time(), locations: []}
                    forecasts = json.loads(locations.to_json())
                    forecast["timestamp"] = time.time()
                except Exception as e:
                    self.log.warning(f"Failed to convert forecast to json: {e}")
                    return dfd
                try:
                    with open(forecast_cache_file, "w") as f:
                        json.dump(forecast, f)
                except Exception as e:
                    self.log.warning(
                        f"Failed to write forecast cache file {forecast_cache_file}: {e}"
                    )

        if station_id is None:
            return locations
        else:
            return dfd


async def get_data(cl, dwd, station=10865):
    df = dwd.station_forecast(station)
    if df is not None:
        # parse df index to numpy datetime array:
        dt = df.index.to_pydatetime()
        # convert to julian date:
        dj = [IndraEvent.datetime2julian(d.astimezone(timezone.utc)) for d in dt]
        tc = df["TTT"].to_numpy()
        # zip dj and tc to list of tuples and ommit nan values for tc:
        dj_temp = [(d, round(t - 273.15, 2)) for d, t in zip(dj, tc) if not np.isnan(t)]

        ie = IndraEvent()
        ie.domain = f"$forecast/dwd/{station}/temperature"
        ie.data = json.dumps(dj_temp)
        ie.data_type = "vector/tuple/jd/float"
        await cl.info(f"Sending event {ie.data}")
        await cl.send_event(ie)


if __name__ == "__main__":
    module_name = "dwd_forecast"
    log_handler = logging.StreamHandler(sys.stderr)
    log_formatter = logging.Formatter(
        "[%(asctime)s]  %(levelname)s [%(module)s::DWD_Forecast] %(message)s"
    )
    log_handler.setFormatter(log_formatter)
    log = logging.getLogger(module_name)
    log.addHandler(log_handler)

    if len(sys.argv) < 3:
        log.error(
            "Missing parameter for dwd_forecast.py, usage: dwd_forecast.py <station-id> <cache-directory> [<poll-rate>] [profile]",
        )
        sys.exit(1)

    station_id = int(sys.argv[1])
    cache_directory = sys.argv[2]
    if len(sys.argv) > 3:
        timer_value = int(sys.argv[3])
    else:
        timer_value = 3600
    if len(sys.argv) > 4:
        profile = sys.argv[4]
    else:
        profile = None

    dwd = DWD(cache_directory=cache_directory, log_handler=log_handler)

    async def main(timer_value=900):
        cl = IndraClient(
            profile=profile,
            verbose=True,
            log_handler=log_handler,
            module_name=module_name,
        )
        ws = await cl.init_connection(verbose=True)
        if ws is None:
            log.error("Could not create Indrajala client for dwd data")
            return
        else:
            await cl.info(
                f"Indrajala client for dwd weather data created, poll-rate {timer_value} seconds"
            )
        while True:
            await cl.info("Polling DWD weather data")
            await get_data(cl, dwd, station=station_id)
            await asyncio.sleep(timer_value)

    asyncio.run(main(timer_value=timer_value))
