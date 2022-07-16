import os
import logging
from hashlib import md5
import urllib.request as request
import pickle

class Downloader:
    def __init__(self, cache_dir='download_cache', use_cache=True):
        self.cache_dir = cache_dir
        self.use_cache = use_cache
        self.log = logging.getLogger("Downloader")
        if use_cache is True:
            if os.path.isdir(cache_dir) is True:
                return
            try:
                os.makedirs(cache_dir)
                self.log.info(f"Cache directory {cache_dir} created.")
            except Exception as e:
                self.use_cache = False
                self.log.error(f"Failed to create cache {cache_dir}: {e}")

    def transform(self, data, transforms):
        if transforms is None:
            return data
        trs=[ t.strip().lower() for t in transforms.split(",") ]
        for t in trs:
            if t=='decode':
                data=data.decode('utf-8')
                continue
            if t=='unpickle':
                data=pickle.loads(data)
                continue
            self.log.error(f"Unknown transform {t}, ignored.")
        return data

    def get(self, url, cache=True, transforms=None):
        """ Transforms: comma separated string containing 'pickle' and/or 'decode' """
        url_comps=url.rsplit('/', 1)
        if len(url_comps)==0:
            self.log.error(f"Invalid url {url}")
            return None
        cache_filename=url_comps[-1]+"_"+md5(url.encode('utf-8')).hexdigest()
        cache_path = os.path.join(self.cache_dir, cache_filename)
        if self.use_cache is True and cache is True:
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, 'rb') as f:
                        data=f.read()
                except Exception as e:
                    self.log.error(f"Failed to read cache {cache_path} for {url}: {e}")
                    return None
                self.log.info(f"Read {url} from cache at {cache_path}")
                if len(data)>0:
                    data=self.transform(data, transforms)
                    return data
        else:
            cache = False
        self.log.info(f"Starting download from {url}...")
        try:
            response = request.urlopen(url)
            data = response.read()
        except Exception as e:
            print(f"Failed to download from {url}: {e}")
            return None
        self.log.info(f"Download from {url}: OK.")
        if cache is True:
            try:
                with open(cache_path, 'wb') as f:
                    f.write(data)
            except Exception as e:
                self.log.warning(f"Failed to save to cache at {cache_path} for {url}: {e}")
        data=self.transform(data,transforms)
        return data

if __name__ == "__main__":
    source_url='https://www.ncei.noaa.gov/pub/data/paleo/pages2k/EuroMed2k/eujja_2krecon_nested_cps.txt'
    source2_url='https://www.ncei.noaa.gov/pub/data/paleo/reconstructions/climate12k/temperature/version1.0.0/Temp12k_v1_0_0.pkl'
    logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s %(message)s', level=logging.INFO)
    dl=Downloader()
    text=dl.get(source_url,transforms='decode')
    data2=dl.get(source2_url,transforms='unpickle')
    print(f"Length of data1: {len(text)}, data2: {len(data2)}")

