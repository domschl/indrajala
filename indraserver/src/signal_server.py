import logging
import os
import time
import signal
import atexit
from datetime import datetime
from zoneinfo import ZoneInfo
import multiprocessing as mp

# XXX dev only
import sys

path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "indralib/src"
)
sys.path.append(path)
from indra_event import IndraEvent  # type: ignore


def indra_process(event_queue, send_queue, config_data):
    print(config_data)
    while True:
        time.sleep(1.0)
        event_queue.put("Hello!")
        
