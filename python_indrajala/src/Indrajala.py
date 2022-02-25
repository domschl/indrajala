# Filename: {time}_{domain}_{uuid4}.json
import uuid
import os
import datetime
from zoneinfo import ZoneInfo
import pandas as pd
from bs4 import BeautifulSoup
import json

__VERSION__ = "base/1.0.0"

class IndrajalaEvent:
    def __init__(self, domain, to_scope, from_instance, auth_hash, location, data_type, from_uuid4=None):
        self.version = __VERSION__
        self.domain = domain
        self.to_scope = to_scope
        if from_uuid4 is None:
            self.from_uuid4 = str(uuid.uuid4())
        else:
            self.from_uuid4 = from_uuid4
        self.from_instance = from_instance
        self.auth_hash = auth_hash
        self.data_type = data_type
        self.location = location

    def set_data(self, data, utcisotime=None, utcisotime_end=None):
        if utcisotime is None:
            self.time = datetime.datetime.utcnow().replace(tzinfo=ZoneInfo('UTC')).isoformat()  # or  'now()' and 'localtime'
        else:
            self.time = utcisotime
        self.utcisotime_end = utcisotime_end
        self.data = data
        self.uuid4 = str(uuid.uuid4())
        return self

class IndrajalaEventSource:
    def __init__(self, config_file=None, save_config_file=None, persistent_storage_root=None, domain=None, to_scope=None, from_instance=None, data_type=None, location=None, auth_hash=None, from_uuid4=None):
        if config_file is not None:
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)
            except Exception as e:
                print(f"Error while loading config file: {e}")
                raise e
            self.persistent_storage_root = config["persistent_storage_root"]
            self.domain = config["domain"]
            self.to_scope = config["to_scope"]
            self.from_instance = config["from_instance"]
            self.data_type = config["data_type"]
            self.location = config["location"]
            self.auth_hash = config["auth_hash"]
            self.from_uuid4 = config["from_uuid4"]
        else:
            self.persistent_storage_root = persistent_storage_root
            self.domain = domain
            self.to_scope = to_scope
            self.from_instance = from_instance
            self.data_type = data_type
            self.location = location
            self.auth_hash = auth_hash
            self.from_uuid4 = from_uuid4

        if self.from_uuid4 is None:
            self.from_uuid4 = str(uuid.uuid4())
        if auth_hash is None:
            auth_hash = ""
        # check input
        if os.path.exists(self.persistent_storage_root) is False or os.path.isdir(self.persistent_storage_root) is False:
             raise Exception(f"persistent_storage_root {self.persistent_storage_root} is not a directory.")
        if self.domain is None:
            raise Exception("domain is not set.")
        if self.to_scope is None:
            raise Exception("to_scope is not set.")
        if self.from_instance is None:
            raise Exception("from_instance is not set.")
        if self.data_type is None:
            raise Exception("data_type is not set.")
        if self.location is None:
            raise Exception("location is not set.")
        if self.auth_hash is None:
            raise Exception("auth_hash is not set.")
        if self.from_uuid4 is None:
            raise Exception("from_uuid4 is not set.")
            
        if save_config_file is not None:
            config = {
                "persistent_storage_root": self.persistent_storage_root,
                "domain": self.domain,
                "to_scope": self.to_scope,
                "from_instance": self.from_instance,
                "data_type": self.data_type,
                "location": self.location,
                "auth_hash": self.auth_hash,
                "from_uuid4": self.from_uuid4
            }
            with open(save_config_file, "w") as f:
                json.dump(config, f, indent=4)
        self.indrajala_event = IndrajalaEvent(domain=domain, to_scope=to_scope, from_instance=from_instance, auth_hash=auth_hash, location=location, data_type=data_type, from_uuid4=from_uuid4)

    def _gen_filename(self, utctime=None):
        if utctime is None:
            utctime = datetime.datetime.utcnow().replace(tzinfo=ZoneInfo('UTC')).isoformat()
        invalids = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        fn=f"{utctime}_{self.from_uuid4}.json"
        for invalid in invalids:
            fn = fn.replace(invalid, '_')
        fp=os.path.join(self.persistent_storage_root, self.domain)
        if not os.path.exists(fp):
            os.makedirs(fp)
        fn = os.path.join(fp, fn)
        return fn

    def set_data(self, data, datetime_with_any_timezone=None, datetime_with_any_timezone_end=None, domain=None):
        if datetime_with_any_timezone is None:
            utcisotime = datetime.datetime.utcnow().replace(tzinfo=ZoneInfo('UTC')).isoformat()  # or  'now()' and 'localtime'
        else:
            utcisotime = datetime_with_any_timezone.astimezone(ZoneInfo('UTC')).isoformat()
        self.indrajala_event.time = utcisotime
        if datetime_with_any_timezone_end is None:
            utcisotime_end = utcisotime  # or  'now()' and 'localtime'
        else:
            utcisotime_end = datetime_with_any_timezone_end.astimezone(ZoneInfo('UTC')).isoformat()
        self.indrajala_event.set_data(data, utcisotime, utcisotime_end)
        if domain is not None:
            self.indrajala_event.domain = domain
            self.domain = domain  # hmm
        filename = self._gen_filename(utcisotime)
        with open(filename, "w") as f:
            json.dump(self.indrajala_event.__dict__, f, indent=4)
        return self

class IndrajalaReport:
    def __init__(self, persistent_storage_root):
        self.persistent_storage_root = persistent_storage_root
        if os.path.exists(self.persistent_storage_root) is False or os.path.isdir(self.persistent_storage_root) is False:
             raise Exception(f"persistent_storage_root {self.persistent_storage_root} is not a directory.")

    def compile_dataframe(self, domain, columns):
        fp=os.path.join(self.persistent_storage_root, domain)
        if 'time' not in columns:
            columns.append('time')
        if not os.path.exists(fp):
            raise Exception(f"domain {domain} does not exist.")
        files = os.listdir(fp)
        if len(files) == 0:
            print(f"No data found for {domain}")
            return None

        df = None
        for file in files:
            with open(os.path.join(fp, file), "r") as f:
                data = json.load(f)
            for column in columns:
                if column not in data and column not in data['data']:
                    raise Exception(f"column {column} does not exist in data for domain {domain}")
            row0 = {column : data[column] for column in data if column in columns}
            row1 = {column : data['data'][column] for column in data['data'] if column in columns}
            row = row0 | row1
            if df is None:
                df = pd.DataFrame(row, index=['time'])
            else:
                df = df.append(row, ignore_index=True)
        return df

