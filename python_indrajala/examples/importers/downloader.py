import os
import logging
from hashlib import md5
import urllib.request as request
import pickle
import re
import io
import pandas as pd
import requests
try:
    import cloudscraper
    cloudscraper_available=True
except ImportError:
    pass

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
                self.log.debug(f"Cache directory {cache_dir} created.")
            except Exception as e:
                self.use_cache = False
                self.log.error(f"Failed to create cache {cache_dir}: {e}")

    def decode(self, data, encoding_name):
        return data.decode(encoding_name)

    def unpickle(self, data):
        return pickle.loads(data)

    def extract_lines(self, data, start, stop=0):
        lines=data.split('\n')
        if stop==0:
            stop=len(lines)
        if start<0:
            start=len(lines)+start
        if stop<0:
            stop=len(lines)+stop
        if start<1 or stop<=start:
            self.log.error(f"Format required: extract_lines(start_line_no:end_line_no), e.g. extract_lines(10:100)")
            self.log.error(f"start_line_no >=1 and end_line_no>start_line_no")
            return None
        if stop>len(lines):
            self.log.error(f"Format required: extract_lines(start_line_no:end_line_no), e.g. extract_lines(10:100)")
            self.log.error(f"end_line_no {stop} is > line-count in source file: {len(lines)}")
            return None
        data='\n'.join(lines[start-1:stop])
        lno=len(data.split('\n'))
        self.log.debug(f"Extracted {lno} lines, [{start}:{stop}]")
        return data

    def extract_html_table(self, data, index):
        tables=pd.read_html(data)
        if len(tables)>index:
            return tables[index]
        else:
            lno=len(tables)
            self.log.error(f"No table with index {index}, table count is {lno}")
            return None

    def pandas_csv_separator(self, data, sep):
        if sep==' ':
            return pd.read_csv(io.StringIO(data), delim_whitespace=True, engine='python')
        return pd.read_csv(io.StringIO(data), sep=sep, engine='python')

    def pandas_filter(self, data, column_list):
        return data.filter(column_list, axis=1)

    def pandas_csv_separator_nan(self, data, sep, nan):
        if sep==' ':
            return pd.read_csv(io.StringIO(data), delim_whitespace=True, na_values=nan, engine='python')
        return pd.read_csv(io.StringIO(data), sep=sep, na_values=nan, engine='python')

    def pandas_excel_rowskips(self, data, skiprow_list):
        return pd.read_excel(data, skiprows=skiprow_list)

    def pandas_excel_worksheet_subset(self, data, worksheet_name, include_rows, include_columns):
        return pd.read_excel(data, sheet_name=worksheet_name, skiprows=lambda x: x+1 not in range(include_rows[0], include_rows[1]+1), usecols=include_columns)

    def single_transform(self, data, transform):
        for t in transform:
            if len(t)>0:
                tf=getattr(self, t[0])
                if tf is not None:
                    data=tf(data,*t[1:])
                else:
                    self.log.error("Transform {t[0]} isn't available!")
                    return None
        return data

    def add_prefix(self, data, prefix):
        return prefix+'\n'+data

    def replace(self, data, token, replacement):
        return data.replace(token, replacement)

    def transform(self, data, transforms):
        data_dict={}
        if transforms is None:
            return data
        for dataset_name in transforms:
            dataset=self.single_transform(data,transforms[dataset_name])
            if dataset is not None:
                data_dict[dataset_name]=dataset
        return data_dict

    def get(self, url, cache=True, transforms=None, user_agent=None):
        url_comps=url.rsplit('/', 1)
        if len(url_comps)==0:
            self.log.error(f"Invalid url {url}")
            return None
        fn=url_comps[-1]
        if '=' in fn:
            url_comps=fn.rsplit('=', 1)
        cache_filename=url_comps[-1]  # +"_"+md5(url.encode('utf-8')).hexdigest()
        cache_path = os.path.join(self.cache_dir, cache_filename)
        if self.use_cache is True and cache is True:
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, 'rb') as f:
                        data=f.read()
                        dl=True
                except Exception as e:
                    self.log.error(f"Failed to read cache {cache_path} for {url}: {e}")
                    return None
                self.log.debug(f"Read {url} from cache at {cache_path}")
                if len(data)>0:
                    data=self.transform(data, transforms)
                    return data
        else:
            cache = False
        self.log.debug(f"Starting download from {url}...")
        data=None
        if user_agent is not None:
            req = request.Request(
                url, 
                data=None, 
                headers={
                    'user-agent': user_agent,
                    'accept': '*/*'
                }
            )
            self.log.info(f"Downloading with user_agent set to: {user_agent}")
            dl=False
            
            try:
                response = request.urlopen(req)
                data = response.read()
                dl=True
            except Exception as e:
                self.log.error(f"Failed to download from {url}: {e}")
                return None
        else:
            try:
                response = request.urlopen(url)
                data = response.read()
            except Exception as e:
                self.log.error(f"Failed to download from {url}: {e}")
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

