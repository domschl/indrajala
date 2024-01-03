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

from indra_serverlib import ProcLog
    
def indra_process(event_queue, send_queue, config_data):
    # print(config_data)
    log = ProcLog(config_data["loglevel"], event_queue)
    while True:
        time.sleep(1.0)
        log.info("Hello!")
        
