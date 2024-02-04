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
    cl = IndraClient(verbose=True, profile="default")
    if cl is None:
        logging.error("Could not create Indrajala client")
        return
    ws = await cl.init_connection(verbose=True)
    print("Connected.")
    if ws is None:
        logging.error("Could not connect to Indrajala")
        return
    await cl.subscribe(["$event/#"])
    print("Subed.")
    await cl.get_wait_history(
        "$event/measurement/temperature/climate/home", None, None, 10
    )
    print("evented.")


logging.basicConfig(level=logging.INFO)
try:
    asyncio.get_event_loop().run_until_complete(tester())
except KeyboardInterrupt:
    pass
