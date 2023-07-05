import os
import sys
from datetime import datetime
import zoneinfo
import json
import asyncio

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

from indra_evqent import IndraEvent
from indra_client import IndraClient


async def indra_connection():
    # get directory of this file:
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config_file = os.path.join(dir_path, "ws_indra.toml")
    try:
        cl = IndraClient(
            config_file=config_file, verbose=True, module_name="wetter_uni_muenchen"
        )
        await cl.init_connection(verbose=True)
    except:
        print("Could not create Indrajala client")
        raise
    await cl.info(
        "Weather client Meteorologisches Institut, München Theresienstr. 37, started."
    )
    return cl


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
            print("Invalid format for table 0, relative feuchte")
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
            print(f"Failed to send event: {e}")
            return


if __name__ == "__main__":
    if len(sys.argv) > 1:
        timer_value = int(sys.argv[1])
    else:
        timer_value = 900

    async def main(timer_value=900):
        cl = await indra_connection()
        if cl is None:
            print("Could not create Indrajala client")
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
