import os
import logging
import io
import tomlkit
import pandas as pd

from downloader import Downloader

def get_temperature_datasets():
    logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s %(message)s', level=logging.INFO)
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
            try:
                with open(filepath,'r') as f:
                    data_desc=tomlkit.parse(f.read())
            except Exception as e:
                logging.error(f"Failed to read toml file {filepath}: {e}")
                continue
            req=['citation/data_source', 'citation/short_title', 'transform/downloader_transforms', 'transform/csv_separator']
            for r in req:
                pt=r.split('/')
                if len(pt)!=2:
                    logging.error(f"req-field doesn't parse: {r}")
                    continue
                if pt[0] not in data_desc:
                    logging.error(f"{filepath} doesn't have [{pt[0]}] section.")
                    continue
                if pt[1] not in data_desc[pt[0]]:
                    logging.error(f"{filepath} doesn't have a {pt[1]}= entry in [{pt[0]}] section.")
                    continue
            data=dl.get(data_desc['citation']['data_source'],transforms=data_desc['transform']['downloader_transforms'])
            sep=data_desc['transform']['csv_separator']
            if sep==' ':
                df=pd.read_csv(io.StringIO(data), delim_whitespace=True, skiprows=data_desc['transform']['csv_skiprows'])
            else:
                df=pd.read_csv(io.StringIO(data), sep=sep, skiprows=data_desc['transform']['csv_skiprows'])
            dfs[data_desc['citation']['short_title']]=df
    return dfs
            