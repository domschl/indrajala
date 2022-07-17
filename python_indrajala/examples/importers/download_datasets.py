import os
import logging
import io
import tomlkit
import pandas as pd

from downloader import Downloader

def get_datasets(log=logging):
    # logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s %(message)s', level=logging.INFO)
    dl=Downloader()
    # source_url='https://www.ncei.noaa.gov/pub/data/paleo/pages2k/EuroMed2k/eujja_2krecon_nested_cps.txt'
    # source2_url='https://www.ncei.noaa.gov/pub/data/paleo/reconstructions/climate12k/temperature/version1.0.0/Temp12k_v1_0_0.pkl'
    # text=dl.get(source_url,transforms='decode')
    # data2=dl.get(source2_url,transforms='unpickle')
    # print(f"Length of data1: {len(text)}, data2: {len(data2)}")
    data_sources_dir="data_sources"

    dfs={}
    for file in os.listdir(data_sources_dir):
        if file.endswith(".toml"):
            filepath=os.path.join(data_sources_dir, file)
            log.info(f"processing: {filepath}")
            try:
                with open(filepath,'r') as f:
                    data_desc=tomlkit.parse(f.read())
            except Exception as e:
                log.error(f"Failed to read toml file {filepath}: {e}")
                continue
            req=['citation/data_source', 'datasets']
            for r in req:
                pt=r.split('/')
                if len(pt)==1:
                    if pt[0] not in data_desc:
                        log.error(f"{filepath} doesn't have [{pt[0]}] section.")
                        continue
                    continue
                if len(pt)!=2:
                    log.error(f"req-field doesn't parse: {r}")
                    continue
                if pt[0] not in data_desc:
                    log.error(f"{filepath} doesn't have [{pt[0]}] section.")
                    continue
                if pt[1] not in data_desc[pt[0]]:
                    log.error(f"{filepath} doesn't have a {pt[1]}= entry in [{pt[0]}] section.")
                    continue
            print("----------------------------------------------------------------------------------")
            print(f"Processing {filepath}")
            data_dicts=dl.get(data_desc['citation']['data_source'],transforms=data_desc['datasets'])
            for dataset in data_dicts:
                print(f">>> {dataset}")
                data=data_dicts[dataset]
                if type(data)==str:
                    print(data)
                else:
                    print(data.head())
                    print("...")
                    print(data.tail())
                dfs[dataset]=data
    return dfs
            