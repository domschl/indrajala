import os
import logging
from hashlib import md5
import urllib.request as request

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

    def get(self, url, decode=False, cache=True):
        url_comps=url.rsplit('/', 1)
        if len(url_comps)==0:
            self.log.error(f"Invalid url {url}")
            return None
        cache_filename=url_comps[-1]+"_"+md5(url.encode('utf-8')).hexdigest()
        cache_path = os.path.join(self.cache_dir, cache_filename)
        if self.use_cache is True and cache is True:
            if os.path.exists(cache_path):
                if decode is True:
                    try:
                        with open(cache_path, 'r') as f:
                            data=f.read()
                    except Exception as e:
                        self.log.error(f"Failed to read cache {cache_path} for {url}: {e}")
                        return None
                    self.log.info(f"Read {url} from cache at {cache_path}")
                    return data
                else:
                    try:
                        with open(cache_path, 'rb') as f:
                            data=f.read()
                    except Exception as e:
                        self.log.error(f"Failed to read cache {cache_path} for {url}: {e}")
                        return None
                    self.log.info(f"Read {url} from cache at {cache_path}")
                    return data
        else:
            cache = False
        self.log.info("Starting download from {url}...")
        try:
            response = request.urlopen(url)
            bin_data = response.read()
        except Exception as e:
            print(f"Failed to download from {url}: {e}")
            return None
        self.log.info(f"Download from {url}: OK.")
        if decode is True:
            data=bin_data.decode('utf-8')
            if cache is True:
                try:
                    with open(cache_path, 'w') as f:
                        f.write(data)
                except Exception as e:
                    self.log.warning(f"Failed to save to cache at {cache_path} for {url}: {e}")
            return data
        else:
            if cache is True:
                try:
                    with open(cache_path, 'wb') as f:
                        f.write(bin_data)
                except Exception as e:
                    self.log.warning(f"Failed to save to cache at {cache_path} for {url}: {e}")
            return bin_data

if __name__ == "__main__":
    source_url='https://www.ncei.noaa.gov/pub/data/paleo/pages2k/EuroMed2k/eujja_2krecon_nested_cps.txt'
    logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s %(message)s', level=logging.INFO)
    dl=Downloader()
    text=dl.get(source_url)
    print(f"Length of data: {len(text)}")

