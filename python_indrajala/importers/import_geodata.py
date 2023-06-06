import logging
import asyncio
import os
import sys

# XXX temporary hack to import from src
path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
print(path)
sys.path.append(path)

from indralib.indra_event import IndraEvent
from indralib.indra_client import IndraClient
from indralib.indra_downloader import IndraDownloader

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s", level=logging.INFO
)
dl = IndraDownloader(cache_dir="geodata/cache")
dfs = dl.get_datasets(data_sources_dir="geodata/data_sources")
for df_name in dfs:
    print("-----------------------------------------------")
    print(df_name)
    print(dfs[df_name]["metadata"])
    print(dfs[df_name]["data"].head())
print(f"Number of datasets: {len(dfs)}")
