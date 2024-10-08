import asyncio
import logging
import os

# Add the parent directory to the path so we can import the client
import sys

path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "indralib/src"
)
print(path)
sys.path.append(path)
from indra_event import IndraEvent  # type: ignore
from indra_client import IndraClient  # type: ignore


async def tester():
    cl = IndraClient(verbose=False, profile="default")
    if cl is None:
        logging.error("Could not create Indrajala client")
        return
    ws = await cl.init_connection(verbose=False)
    print("Connected.")
    if ws is None:
        logging.error("Could not connect to Indrajala")
        return
    await cl.subscribe(["$event/#"])
    doms = await cl.get_wait_unique_domains(
        domain="$event/%", data_type="number/float%"
    )
    print(f"Domains: {doms}")
    temp = await cl.get_wait_last_event(
        domain="$event/measurement/temperature/climate/home"
    )
    if temp is not None:
        print(
            f"Temp: {temp.data} at {IndraEvent.julian_to_datetime(temp.time_jd_start)}"
        )
    else:
        print(f"Not found!")
    hist = await cl.get_wait_history(
        "$event/measurement/temperature/climate/home", None, None, 3, "Sequential"
    )
    print(hist)


logging.basicConfig(level=logging.INFO)
try:
    asyncio.get_event_loop().run_until_complete(tester())
except KeyboardInterrupt:
    pass
