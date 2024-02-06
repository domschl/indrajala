# %%
import asyncio
import logging
import os

import nest_asyncio

nest_asyncio.apply()

# Add the parent directory to the path so we can import the client
import sys

path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "indralib/src"
)
print(path)
sys.path.append(path)
from indra_event import IndraEvent  # type: ignore
from indra_client import IndraClient  # type: ignore

cl = IndraClient(verbose=False, profile="default")
if cl is None:
    logging.error("Could not create Indrajala client")
ws = await cl.init_connection(verbose=False)
print("Connected.")


# %%
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
        print(f"Temp: {temp.data} at {IndraEvent.julian2datetime(temp.time_jd_start)}")
    else:
        print(f"Not found!")
    hist = await cl.get_wait_history(
        "$event/measurement/temperature/climate/home", None, None, 3, "Sequential"
    )
    print(hist)


# %%
logging.basicConfig(level=logging.INFO)
try:
    await tester()
except KeyboardInterrupt:
    pass
# %%
cl = IndraClient(verbose=False, profile="default")
if cl is None:
    logging.error("Could not create Indrajala client")
ws = await cl.init_connection(verbose=False)
print("Connected.")

# %%
# uuid4s = ["c3cdca72-9a4d-4c04-a359-d449a11dbfd5"]
domains = ["$event/measurement/%"]
# await cl.delete_recs_wait(uuid4s=uuid4s)
await cl.delete_recs_wait(domains=domains)
# %%
# test data array of tuples utc datetime and random float:
import datetime
import random

data = [
    (
        datetime.datetime(2021, 1, 1, 0, 0, 0).replace(tzinfo=datetime.timezone.utc),
        random.random(),
    ),
    (
        datetime.datetime(2021, 1, 2, 0, 0, 0).replace(tzinfo=datetime.timezone.utc),
        random.random(),
    ),
    (
        datetime.datetime(2021, 1, 3, 0, 0, 0).replace(tzinfo=datetime.timezone.utc),
        random.random(),
    ),
]

# create array of IndraEvent json objects:
events = []
for d in data:
    ev = IndraEvent()
    ev.domain = "$event/measurement/testdata"
    ev.time_jd_start = IndraEvent.datetime2julian(d[0])
    ev.from_id = "ws/python/testdata"
    ev.data_type = "number/float"
    ev.data = d[1]
    events.append(ev.to_dict())

# %%
ret = await cl.update_recs_wait(events)
print(ret)
# %%
await cl.delete_recs_wait(domains="$event/measurement/testdata")
# %%
