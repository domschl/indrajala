import json
import time
import os

# path = os.path.join(
#     os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
#     "indralib/src",
# )
# sys.path.append(path)
from indralib.indra_event import IndraEvent  # type: ignore
from indralib.indra_time import IndraTime  # type: ignore
from indralib.indra_downloader import IndraDownloader

from indra_serverlib import IndraProcessCore


class IndraProcess(IndraProcessCore):
    def __init__(
        self,
        config_data,
        transport,
        event_queue,
        send_queue,
        zmq_event_queue_port,
        zmq_send_queue_port,
    ):
        super().__init__(
            config_data,
            transport,
            event_queue,
            send_queue,
            zmq_event_queue_port,
            zmq_send_queue_port,
            mode="dual",
        )
        self.data_sources_directory = os.path.expanduser(
            config_data["data_sources_directory"]
        )
        self.data_cache_directory = os.path.expanduser(
            config_data["data_cache_directory"]
        )
        if os.path.exists(self.data_sources_directory) is False:
            self.log.warning(
                f"Data sources directory {self.data_sources} does not exist, disabling importer, no work."
            )
            self.bConnectActive = False
        else:
            if os.path.exists(self.data_cache_directory) is False:
                os.makedirs(self.data_cache_directory)
            self.bConnectActive = False
            self.init_downloads()

    def init_downloads(self):
        self.downloader = IndraDownloader(cache_dir=self.data_cache_directory)
        self.dfs = self.downloader.get_datasets(
            data_sources_dir=self.data_sources_directory
        )
        self.log.info(f"Data sources: {len(self.dfs)}")
        self.bConnectActive = True

    def inbound_init(self):
        return True

    def inbound(self):
        time.sleep(1)
        return None

    def outbound(self, ev: IndraEvent):
        self.log.warning(f"Publish-request from {ev.from_id}, {ev.domain} to IMPORTER")

    def shutdown(self):
        pass
