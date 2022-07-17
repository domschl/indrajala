import os
import logging
from hashlib import md5
import urllib.request as request
import pickle
import re
import io
import pandas as pd

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

    def single_transform(self, data, transform):
        trs=[ t.strip().lower() for t in transform.split(",") ]  # XXX bad parser!
        for t in trs:
            if t=='decode_utf8':
                data=data.decode('utf-8')
                continue
            if t=='decode_latin1':
                data=data.decode('latin1')
                continue
            if t=='unpickle':
                data=pickle.loads(data)
                continue
            ft=re.search('extract_lines\((.+?)\)',t)
            if ft is not None:
                prs=ft.group(1).split(':')
                if len(prs)!=2:
                    self.log.error(f"Format required: extract_lines(start_line_no:end_line_no), e.g. extract_lines(10:100)")
                    return None
                lines=data.split('\n')
                if prs[1]=="":
                    prs[1]=str(len(lines))
                s0=int(prs[0])
                s1=int(prs[1])
                if s0<0:
                    s0=len(lines)+s0
                if s1<0:
                    s1=len(lines)+s1
                if s0<1 or s1<=s0:
                    self.log.error(f"Format required: extract_lines(start_line_no:end_line_no), e.g. extract_lines(10:100)")
                    self.log.error(f"start_line_no >=1 and end_line_no>start_line_no")
                    return None
                if s1>len(lines):
                    self.log.error(f"Format required: extract_lines(start_line_no:end_line_no), e.g. extract_lines(10:100)")
                    self.log.error(f"end_line_no {s1} is > line-count in source file: {len(lines)}")
                    return None
                data='\n'.join(lines[s0-1:s1])
                ln=len(data.split('\n'))
                self.log.info(f"Extract {ln} lines, [{s0}:{s1}]")
                continue
            ft=re.search("csv_separator\('(.+?)'\)",t)
            if ft is not None:
                sep=ft.group(1)
                if sep==' ':
                    data=pd.read_csv(io.StringIO(data), delim_whitespace=True)
                    continue
                if sep=='\t':
                    data=pd.read_csv(io.StringIO(data), sep='\t')
                    continue
                if sep==';':
                    data=pd.read_csv(io.StringIO(data), sep=';')
                    continue
                self.log.error(f"Unexpected csv_separator {sep}, possible values are ' ','\\t',';'")
            self.log.error(f"Unknown transform {t}, ignored.")
        return data

    def transform(self, data, transforms):
        data_dict={}
        if transforms is None:
            return data
        for dataset_name in transforms:
            dataset=self.single_transform(data,transforms[dataset_name])
            if dataset is not None:
                data_dict[dataset_name]=dataset
        return data_dict

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

