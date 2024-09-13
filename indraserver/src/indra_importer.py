import json
import time
import os

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
        self.downloaders = []
        self.dfss = []
        self.data_sources_directories = config_data["data_sources_directories"]
        self.data_cache_directory = os.path.expanduser(
            config_data["data_cache_directory"]
        )
        self.data_sources_state_file = os.path.expanduser(
            config_data["data_sources_state_file"]
        )
        self.bConnectActive = False
        for dir in self.data_sources_directories:
            dir = os.path.expanduser(dir)
            if os.path.exists(dir) is False:
                self.log.warning(
                    f"Data sources directory {dir} does not exist, disabling importer corresponding importer"
                )
                self.data_sources_directories.remove(dir)
            else:
                self.log.info(f"Data sources directory {dir} found")
        if len(self.data_sources_directories) == 0:
            self.log.error(
                "No valid data sources directories found, importer disabled."
            )
        else:
            self.bConnectActive = True

    def init_downloads(self):
        for dir in self.data_sources_directories:
            downloader = IndraDownloader(cache_dir=self.data_cache_directory)
            self.downloaders.append(downloader)
            self.log.info(f"Data sources directory: {dir}")
            dfs = downloader.get_datasets(data_sources_dir=dir)
            self.dfss.append(dfs)
            self.log.info(f"Data source {dir}: {len(dfs)} sub-datasets")
        self.bConnectActive = True

    def inbound_init(self):
        if len(self.data_sources_directories) > 0:
            if os.path.exists(self.data_cache_directory) is False:
                os.makedirs(self.data_cache_directory)
            self.log.info(
                f"Initiating {len(self.data_sources_directories)} data sources"
            )
            self.init_downloads()
            return True
        else:
            self.log.warning("No data sources directories found, disabling importer")
        return False

    def inbound(self):
        time.sleep(1)
        return None

    def outbound(self, ev: IndraEvent):
        self.log.warning(f"Publish-request from {ev.from_id}, {ev.domain} to IMPORTER")

    def shutdown(self):
        pass
