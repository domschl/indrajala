import asyncio
import logging
import os

# Add the parent directory to the path so we can import the client
import sys

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
print(path)
sys.path.append(path)
from indralib.indra_event import IndraEvent
from indralib.indra_client import IndraClient


async def tester():
    cl = IndraClient(config_file="ws_indra.toml")
    if cl is None:
        logging.error("Could not create Indrajala client")
        return
    ws = await cl.init_connection(verbose=True)
    if ws is None:
        logging.error("Could not connect to Indrajala")
        return
    await cl.subscribe(["$event/#"])
    hist_future = await cl.get_history(
        "$event/omu/enviro-master/BME280-1/sensor/humidity", 0, None, 100
    )
    if hist_future is None:
        logging.error("Could not get history")
    else:
        hist = await hist_future
        print(hist)
    while True:
        ie = await cl.recv_event()
        if ie is None:
            logging.error("Could not receive event")
            break
        logging.info(f"Received event: {ie.to_json()}")


logging.basicConfig(level=logging.INFO)
try:
    asyncio.get_event_loop().run_until_complete(tester())
except KeyboardInterrupt:
    pass
