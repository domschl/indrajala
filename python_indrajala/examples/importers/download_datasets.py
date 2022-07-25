import os
import logging
import tomlkit

from downloader import Downloader

def get_datasets(log=logging):
    dl=Downloader()
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
            # print("----------------------------------------------------------------------------------")
            # print(f"Processing {filepath}")
            if 'user_agent' in data_desc['citation']:
                ua=data_desc['citation']['user_agent']
            else:
                ua=None
            if 'redirect' in data_desc['citation']:
                use_redirect = data_desc['citation']['redirect']
            else:
                use_redirect = True
            data_dicts=dl.get(data_desc['citation']['data_source'],transforms=data_desc['datasets'],user_agent=ua, resolve_redirects=use_redirect)
            if data_dicts is None:
                log.error(f"Failed to retrieve dataset(s) from {data_desc['citation']['data_source']}")
                continue
            for dataset in data_dicts:
                # print(f">>> {dataset}")
                data=data_dicts[dataset]
                # if type(data)==str:
                #     print(data)
                # else:
                #     print(data.head())
                #     print("...")
                #     print(data.tail())
                dfs[dataset]={}
                dfs[dataset]['data']=data
                dfs[dataset]['metadata']=data_desc['citation']
    return dfs
 
if __name__=="__main__":
    logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s %(message)s', level=logging.INFO)
    dfs=get_datasets()
    print(f"{len(dfs)} datasets available: {dfs.keys()}")

