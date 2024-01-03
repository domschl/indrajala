import os
import sys
from datetime import datetime
import zoneinfo
import json
import asyncio
import logging

import pandas as pd
import bs4
import urllib.request

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

from indra_event import IndraEvent  # type: ignore
from indra_client import IndraClient  # type: ignore


async def get_data(cl):
    url = "https://www.meteo.physik.uni-muenchen.de/mesomikro/stadt/messung.php"
    try:
        html = urllib.request.urlopen(url).read()
        doc = bs4.BeautifulSoup(html, "html.parser")
        df2 = pd.read_html(html)
    except Exception as e:
        await cl.error(f"Download of data at {url} failed: {e}")
        return
    if len(df2) != 4:
        await cl.error(f"Invalid number of tables: {len(df2)}")
        return
    try:
        time = doc.text.split("\n")[8].strip()
        dt = datetime.strptime(time, "%d.%m.%Y %H:%M").astimezone(
            zoneinfo.ZoneInfo("Europe/Berlin")
        )
    except Exception as e:
        await cl.error(f"Could not parse time {time}: {e}")
        return

    try:
        jd = IndraEvent.datetime2julian(dt)
        data = {}
        time_data = {}
        time_data["time"] = dt
        time_data["jd"] = jd
        if df2[0][0][2] == "Lufttemperatur":
            data["temperature"] = df2[0][1][2].split(" ")[0]
        else:
            await cl.warn("Invalid format for table 0, lufttemperatur")
        if df2[0][0][5] == "Relative Feuchte":
            data["humidity"] = df2[0][1][5].split(" ")[0]
        else:
            cl.error("Invalid format for table 0, relative feuchte")
        if df2[0][0][6] == "Windgeschwindigkeit":
            data["wind_speed"] = df2[0][2][6].split(" ")[0]
        else:
            await cl.warn("Invalid format for table 0, windgeschwindigkeit")

        if df2[2][0][1] == "Globalstr.":
            data["solar_radiation"] = df2[2][0][2].split(" ")[0]
        else:
            await cl.warn("Invalid format for table 2, globalstrahlung")
        if df2[2][1][1] == "Diffuse Str.":
            data["diffuse_radiation"] = df2[2][1][2].split(" ")[0]
        else:
            await cl.warn("Invalid format for table 2, diffuse strahlung")
        if df2[2][2][1] == "Atm.Gegenstr.":
            data["atmospheric_radiation"] = df2[2][2][2].split(" ")[0]
        else:
            await cl.warn("Invalid format for table 2, atm. gegenstrahlung")
        if df2[2][4][1] == "UV-Index":
            data["uv_index"] = df2[2][4][2].split(" ")[0]
        else:
            await cl.warn("Invalid format for table 2, uv index")

        if df2[3][0][1] == "Luftdruck 515 m":
            data["pressure"] = df2[3][0][2].split(" ")[0]
        else:
            await cl.warn("Invalid format for table 3, luftdruck")
        if df2[3][1][1] == "Luftdruck NN":
            data["pressureNN"] = df2[3][1][2].split(" ")[0]
        else:
            await cl.warn("Invalid format for table 3, luftdruck NN")
        if df2[3][2][1] == "Windrichtung 30 m Höhe":
            data["wind_direction"] = df2[3][2][2].split(" ")[0]
        else:
            await cl.warn("Invalid format for table 3, windrichtung")
        if df2[3][3][1] == "Niederschlag aktuell":
            data["precipitation"] = df2[3][3][2].split(" ")[0]
        else:
            await cl.warn("Invalid format for table 3, niederschlag")
    except Exception as e:
        await cl.error(f"Could not parse data: {e}")
        return

    for k in data.keys():
        ie = IndraEvent()
        ie.time_jd_start = jd
        ie.domain = f"$event/meterologisches_institut_muenchen/theresienstrasse_37/{k}"
        ie.from_id = "ws/python_indrajala/wetter_uni_muenchen"
        ie.data_type = "number/float"
        ie.data = json.dumps(float(data[k]))
        try:
            await cl.send_event(ie)
        except Exception as e:
            print(f"Failed to send event: {e}", file=sys.stderr)
            return
        await cl.info(f"Sent event {ie.domain} {ie.data_type} {ie.data}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        timer_value = int(sys.argv[1])
    else:
        timer_value = 900
    if len(sys.argv) > 2:
        profile = sys.argv[2]
    else:
        profile = None

    module_name = "wetter_uni_muenchen"
    log_handler = logging.StreamHandler(sys.stderr)
    log_formatter = logging.Formatter(
        "[%(asctime)s]  %(levelname)s [%(module)s::WetterMuc] %(message)s"
    )
    log_handler.setFormatter(log_formatter)
    log = logging.getLogger(module_name)
    log.addHandler(log_handler)

    async def main(timer_value=900):
        cl = IndraClient(
            profile=profile,
            verbose=True,
            log_handler=log_handler,
            module_name=module_name,
        )
        ws = await cl.init_connection(verbose=True)
        if ws is None:
            log.error("Could not create Indrajala client")
            return
        else:
            await cl.info(
                f"Indrajala client for muc uni weather data created, poll-rate {timer_value} seconds"
            )
        while True:
            await cl.info("Polling weather data")
            await get_data(cl)
            await asyncio.sleep(timer_value)

    asyncio.run(main(timer_value=timer_value))
