import os
import logging
from hashlib import md5
import urllib.request as request
import cgi
import pickle
import re
import io
import pandas as pd
import json
import datetime
import requests
import tomllib as toml
import uuid

from indralib.indra_event import IndraEvent
import io

# Requires: pandas, lxml, openpyxl


class IndraDownloader:
    def __init__(self, cache_dir="download_cache", use_cache=True):
        self.cache_dir = cache_dir
        self.use_cache = use_cache
        self.log = logging.getLogger("Downloader")
        if use_cache is True:
            self.cache_info = {}
            if os.path.isdir(cache_dir) is False:
                try:
                    os.makedirs(cache_dir)
                    self.log.debug(f"Cache directory {cache_dir} created.")
                except Exception as e:
                    self.use_cache = False
                    self.log.error(f"Failed to create cache {cache_dir}: {e}")
                    return
            self.cache_info_file = os.path.join(cache_dir, "cache_info.json")
            if os.path.exists(self.cache_info_file):
                try:
                    with open(self.cache_info_file, "r") as f:
                        self.cache_info = json.load(f)
                except Exception as e:
                    self.log.error(f"Failed to read cache_info: {e}")
            # Check for cache consistency, delete inconsistent entries:
            entries = list(self.cache_info.keys())
            for entry in entries:
                valid = True
                for mand in ["cache_filename", "time"]:
                    if mand not in self.cache_info[entry]:
                        self.log.warning(
                            f"Cache-entry for {entry} inconsistent: no {mand} field, deleting entry."
                        )
                        del self.cache_info[entry]
                        valid = False
                        break
                if valid is False:
                    continue
                lpath = os.path.join(
                    self.cache_dir, self.cache_info[entry]["cache_filename"]
                )
                if os.path.exists(lpath) is False:
                    self.log.warning(
                        f"Local file {lpath} for cache entry {entry} does not exist, deleting cache entry."
                    )
                    del self.cache_info[entry]
                    continue

    def update_cache(self, url, cache_filename):
        if self.use_cache:
            for other_url in self.cache_info:
                if other_url == url:
                    continue
                if "cache_filename" in self.cache_info[other_url]:
                    if self.cache_info[other_url]["cache_filename"] == cache_filename:
                        self.log.error(
                            "FATAL cache name clash: {other_url} and {url} both want to cache a file named {cache_filename}"
                        )
                        self.log.error(
                            "Caching will not work for {url}, cache for {other_url} delete too."
                        )
                        self.log.error("-----Algorithm must be changed!------")
                        del self.cache_info[other_url]
                        return
            self.cache_info[url] = {}
            self.cache_info[url]["cache_filename"] = cache_filename
            self.cache_info[url]["time"] = datetime.datetime.now().isoformat()
            try:
                with open(self.cache_info_file, "w") as f:
                    json.dump(self.cache_info, f, indent=4)
                    # self.log.info(f"Saved cache_info to {self.cache_info_file}")
            except Exception as e:
                self.log.error(f"Failed to update cache_info: {e}")

    def decode(self, encoding_name):
        data = self.tf_data
        return data.decode(encoding_name)

    def unpickle(self):
        data = self.tf_data
        return pickle.loads(data)

    def extract_lines(self, start, stop=0):
        data = self.tf_data
        lines = data.split("\n")
        if stop == 0:
            stop = len(lines)
        if start < 0:
            start = len(lines) + start
        if stop < 0:
            stop = len(lines) + stop
        if start < 1 or stop <= start:
            self.log.error(
                f"Format required: extract_lines(start_line_no:end_line_no), e.g. extract_lines(10:100)"
            )
            self.log.error(f"start_line_no >=1 and end_line_no>start_line_no")
            return None
        if stop > len(lines):
            self.log.error(
                f"Format required: extract_lines(start_line_no:end_line_no), e.g. extract_lines(10:100)"
            )
            self.log.error(
                f"end_line_no {stop} is > line-count in source file: {len(lines)}"
            )
            return None
        data = "\n".join(lines[start - 1 : stop])
        lno = len(data.split("\n"))
        self.log.debug(f"Extracted {lno} lines, [{start}:{stop}]")
        return data

    def remove_comments(self, comment_line_start="#"):
        data = self.tf_data
        lines = data.split("\n")
        valid_data = []
        for line in lines:
            if line.startswith(comment_line_start) is False:
                valid_data.append(line)
        valid_data = "\n".join(valid_data)
        return valid_data

    def extract_html_table(self, index):
        data = self.tf_data
        tables = pd.read_html(data)
        if len(tables) > index:
            return tables[index]
        else:
            lno = len(tables)
            self.log.error(f"No table with index {index}, table count is {lno}")
            return None

    def pandas_csv_separator(self, sep):
        data = self.tf_data
        if sep == " ":
            return pd.read_csv(io.StringIO(data), sep=r"\s+", engine="python")
        return pd.read_csv(io.StringIO(data), sep=sep, engine="python")

    def pandas_filter(self, column_list):
        data = self.tf_data
        return data.filter(column_list, axis=1)

    def pandas_csv_separator_nan(self, sep, nan):
        data = self.tf_data
        if sep == " ":
            return pd.read_csv(
                io.StringIO(data), sep=r"\s+", na_values=nan, engine="python"
            )
        return pd.read_csv(io.StringIO(data), sep=sep, na_values=nan, engine="python")

    def pandas_excel_rowskips(self, skiprow_list):
        data = self.tf_data
        # change to use BytesIO:
        data_bio = io.BytesIO(data)
        return pd.read_excel(data_bio, skiprows=skiprow_list)

    def pandas_excel_worksheet_subset(
        self, worksheet_name, include_rows, include_columns
    ):
        data = self.tf_data
        return pd.read_excel(
            data,
            sheet_name=worksheet_name,
            skiprows=lambda x: x + 1 not in range(include_rows[0], include_rows[1] + 1),
            usecols=include_columns,
        )

    def add_prefix(self, prefix):
        data = self.tf_data
        return prefix + "\n" + data

    def replace(self, token, replacement):
        data = self.tf_data
        return data.replace(token, replacement)

    def indra_import(self, time, column):
        self.log.info(f"Indra import: {time}, {column} NOT IMPLEMENTED YET")
        return self.tf_data

    def transform_df(self, df, transform, left, right):
        # XXX this is unsafe code.
        try:
            exec(transform)
        except Exception as e:
            self.log.error(f"Failed to apply transform {transform}: {e}")
            print(df.head(5))
            return None
        return df

    def single_transform(self, data, transform):
        if transform.startswith("df['"):
            ind = transform.find("=")
            if ind == -1:
                self.log.error(
                    f"Format required: df['column_name'] = transform, e.g. df['column_name'] = df['column_name'].str.lower()"
                )
                return None
            left = transform[:ind]
            right = transform[ind + 1 :]
            ind = left.find("']")
            if ind == -1:
                self.log.error(
                    f"Format required: df['column_name'] = transform, e.g. df['column_name'] = df['column_name'].str.lower()"
                )
                return None
            # check, if data is a dataframe
            if isinstance(data, pd.DataFrame) is False:
                self.log.error(f"Data is not a dataframe, cannot apply transform")
                return None
            return self.transform_df(data, transform, left, right)
        else:
            try:
                fn_name = transform.split("(")[0]
            except Exception as e:
                self.log.error(f"Failed to parse transform {transform}: {e}")
                return None
            tf = getattr(self, fn_name)
            if tf is not None:
                trs = "self." + transform
                self.tf_data = data
                try:
                    data = eval(trs)
                except Exception as e:
                    self.log.error(f"Failed to eval {trs}: {e}")
                    return None
            return data

    def transform(self, data, transforms):
        data_dict = {}
        if transforms is None:
            return data
        original_data = data
        for dataset_name in transforms:
            self.log.info(f"Creating dataset {dataset_name}")
            data = original_data
            for transform in transforms[dataset_name]:
                data = self.single_transform(data, transform)
            dataset = data
            if dataset is not None:
                data_dict[dataset_name] = dataset
        return data_dict

    def get(
        self,
        url,
        transforms=None,
        user_agent=None,
        resolve_redirects=True,
    ):
        cache_filename = None
        cache_path = None
        if resolve_redirects is True:
            try:
                # self.log.info(f"Test for redirect: {url}")
                r = requests.get(url, allow_redirects=True)
                # self.log.info(f"ReqInfo: {r}")
                if r.url != url:
                    self.log.warning(f"Redirect resolved: {url}->{r.url}")
                    url = r.url
            except Exception as e:
                self.log.info(f"Could not resolve redirects {e}")
        if self.use_cache is True:
            if url in self.cache_info:
                cache_filename = self.cache_info[url]["cache_filename"]
                cache_path = os.path.join(self.cache_dir, cache_filename)
                cache_time = self.cache_info[url]["time"]

        retrieved = False
        if cache_filename is None:
            try:
                remotefile = request.urlopen(url)
                remote_info = remotefile.info()
                # self.log.info(f"Remote.info: {remote_info}")
                if "Content-Disposition" in remote_info:
                    info = remote_info["Content-Disposition"]
                    value, params = cgi.parse_header(info)
                    # self.log.info(f"header: {params}")
                    if "filename" in params:
                        cache_filename = params["filename"]
                        cache_path = os.path.join(self.cache_dir, cache_filename)
                        self.log.info(f"Local filename is set to {cache_filename}")
                        self.log.info(f"Starting download via retrieve from {url}...")
                        request.urlretrieve(url, cache_path)
                        self.log.info(f"Download from {url}: OK.")
                        retrieved = True
            except Exception as e:
                cache_filename = None
            if retrieved is True:
                self.update_cache(url, cache_filename)
                return
        if cache_filename is None:
            url_comps = url.rsplit("/", 1)
            if len(url_comps) == 0:
                self.log.error(f"Invalid url {url}")
                return None
            fn = url_comps[-1]
            if "=" in fn:
                url_comps = fn.rsplit("=", 1)
            cache_filename = url_comps[-1]
            cache_path = os.path.join(self.cache_dir, cache_filename)
        if self.use_cache is True:
            if os.path.exists(cache_path):
                dl = False
                try:
                    with open(cache_path, "rb") as f:
                        data = f.read()
                        dl = True
                except Exception as e:
                    self.log.error(f"Failed to read cache {cache_path} for {url}: {e}")
                if dl is True:
                    self.log.info(f"Read {url} from cache at {cache_path}")
                    if len(data) > 0:
                        data = self.transform(data, transforms)
                        return data
                    else:
                        self.log.error(f"Ignoring zero-length cache-file {cache_path}")
                        dl = False
        self.log.info(f"Starting download from {url}...")
        data = None
        if user_agent is not None:
            req = request.Request(
                url, data=None, headers={"user-agent": user_agent, "accept": "*/*"}
            )
            self.log.info(f"Downloading with user_agent set to: {user_agent}")
            dl = False

            try:
                response = request.urlopen(req)
                data = response.read()
                dl = True
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
        if self.use_cache is True:
            try:
                with open(cache_path, "wb") as f:
                    f.write(data)
                    self.update_cache(url, cache_filename)
            except Exception as e:
                self.log.warning(
                    f"Failed to save to cache at {cache_path} for {url}: {e}"
                )
        data = self.transform(data, transforms)
        return data

    def get_datasets(self, data_sources_dir):
        dfs = {}
        self.indra_imports = {}
        for file in os.listdir(data_sources_dir):
            if file.endswith(".toml"):
                filepath = os.path.join(data_sources_dir, file)
                self.log.info(f"processing: {filepath}")
                try:
                    with open(filepath, "rb") as f:
                        data_desc = toml.load(f)
                except Exception as e:
                    self.log.error(f"Failed to read toml file {filepath}: {e}")
                    continue
                req = ["citation/data_source", "datasets"]
                for r in req:
                    pt = r.split("/")
                    if len(pt) == 1:
                        if pt[0] not in data_desc:
                            self.log.error(
                                f"{filepath} doesn't have [{pt[0]}] section."
                            )
                            continue
                        continue
                    if len(pt) != 2:
                        self.log.error(f"req-field doesn't parse: {r}")
                        continue
                    if pt[0] not in data_desc:
                        self.log.error(f"{filepath} doesn't have [{pt[0]}] section.")
                        continue
                    if pt[1] not in data_desc[pt[0]]:
                        self.log.error(
                            f"{filepath} doesn't have a {pt[1]}= entry in [{pt[0]}] section."
                        )
                        continue
                # print("----------------------------------------------------------------------------------")
                # print(f"Processing {filepath}")
                if "user_agent" in data_desc["citation"]:
                    ua = data_desc["citation"]["user_agent"]
                else:
                    ua = None
                if "redirect" in data_desc["citation"]:
                    use_redirect = data_desc["citation"]["redirect"]
                else:
                    use_redirect = True
                if "indra_import" in data_desc:
                    indra_imports = data_desc["indra_import"]
                    self.log.info(f"indra_imports: {indra_imports}")
                else:
                    indra_imports = None
                data_dicts = self.get(
                    data_desc["citation"]["data_source"],
                    transforms=data_desc["datasets"],
                    user_agent=ua,
                    resolve_redirects=use_redirect,
                )
                if data_dicts is None:
                    self.log.error(
                        f"Failed to retrieve dataset(s) from {data_desc['citation']['data_source']}"
                    )
                    continue
                for dataset in data_dicts:
                    # print(f">>> {dataset}")
                    data = data_dicts[dataset]
                    # if type(data)==str:
                    #     print(data)
                    # else:
                    #     print(data.head())
                    #     print("...")
                    #     print(data.tail())
                    dfs[dataset] = {}
                    dfs[dataset]["data"] = data
                    dfs[dataset]["metadata"] = data_desc["citation"]
        return dfs
