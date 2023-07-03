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
from indra_event import IndraEvent
from indra_client import IndraClient


async def chat():
    cl = IndraClient(config_file="ws_indra.toml", verbose=False)
    if cl is None:
        logging.error("Could not create Indrajala client")
        return
    ws = await cl.init_connection(verbose=True)
    if ws is None:
        logging.error("Could not connect to Indrajala")
        return
    await cl.subscribe(["CHAT.1/#"])  # XXX $event?!
    # domain_list_future = await cl.get_unique_domains()
    # hist_future = await cl.get_history(
    #     "$event/omu/enviro-master/BME280-1/sensor/humidity", 0, None, 100
    # )
    # if hist_future is None:
    #     logging.error("Could not get history")
    # if domain_list_future is None:
    #     logging.error("Could not get domain list")
    # else:
    #     hist = await hist_future
    #     print(hist)
    while True:
        print("Input: ", end="")
        msg = input()
        if msg == "exit":
            break
        ie = IndraEvent()
        ie.domain = "LLM.1/indra-chat"
        ie.data_type = "string/chat"
        ie.data = msg
        await cl.send_event(ie)
        while True:
            ie = await cl.recv_event(timeout=5)
            if ie is None:
                print()
                break
            else:
                print(
                    ie.data.replace("###", "").replace("##", "").replace("}", ""),
                    end="",
                    flush=True,
                )
                if ie.data.endswith("}"):
                    print()
                    # break


logging.basicConfig(level=logging.INFO)
try:
    asyncio.get_event_loop().run_until_complete(chat())
except KeyboardInterrupt:
    pass
