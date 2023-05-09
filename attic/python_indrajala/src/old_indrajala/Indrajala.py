# Filename: {time}_{domain}_{uuid4}.json
import uuid
import os
import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo
import pandas as pd
# from bs4 import BeautifulSoup
import json

__VERSION__ = "base/1.0.0"

# XXX checkout: https://docs.astropy.org/en/stable/units/index.html

class IndrajalaUnits:
    def init(self):
        self.SI_table = {'count': ('count', 'count', lambda x: float(x)),
                         'cm': ('m', 'm', lambda x: float(x)/100.0),
                         'kg': ('kg', 'g', lambda x: float(x)*1000.0),
                         'count/min': ('hz', 'hz', lambda x: float(x)/60.0),
                         '%': ('%', '%', lambda x: float(x)),
                         'mmHg': ('mmHg', 'Pa', lambda x: float(x)* 133.322387415),
                         'degC': ('degC', 'K', lambda x: float(x)+273.15),
                         'km': ('km', 'm', lambda x: float(x)*1000.0),
                         'kcal': ('kcal', 'J', lambda x: float(x)*4184.0),
                         'min': ('min', 's', lambda x: float(x)*60.0),
                         'm': ('m', 'm', lambda x: float(x)),
                         'mL/min·kg': ('mL/min·kg', 'L/s·kg', lambda x: float(x)/60000.0),
                         'dBASPL': ('dBASPL', 'dBASPL', lambda x: float(x)),
                         'km/hr': ('km/hr', 'm/s', lambda x: float(x)/3.6),
                         'm/s': ('m/s', 'm/s', lambda x: float(x)),
                         'hr': ('hr', 's', lambda x: float(x)*3600.0),
                         'ms': ('ms', 's', lambda x: float(x)/1000.0)
                         }
        self.desc_table = { ('count', 'count',          'N', ''),
                            ('m',     'length',         'l', 'm'),
                            ('kg',    'mass',           'M', 'g'),
                            ('Hz',    'frequency',      'F', 'Hz'),
                            ('%',     'percent',        'p', '%'),
                            ('mmHg',  'pressure',       'P', 'mmHg'),
                            ('degC',  'temperature',    'T', 'degC'),
                            ('km',    'distance',       'd', 'km'),
                            ('kcal',  'energy',         'E', 'kcal'),
                            ('s',     'time',           't', 's'),
                            ('m/s',   'velocity',       'v', 'm/s'),
                            ('dBASPL','sound pressure', 'P', 'dBASPL'),
                            ('km/hr', 'speed',          'v', 'm/s'),
                            ('hr',    'time',           't', 's'),
                            ('ms',    'time',           't', 's')}

    def convertToSI(self, unit, value):
        if unit in self.SI_table:
            return self.SI_table[unit][2](value)
        else:
            return value

class Indrajala:
    def __init__(self, persistent_storage_root):
        self.version = "base/1.0.0"
        self.schema = ['domain', 'to_scope', 'from_instance', 'from_uuid4', 'auth_hash', 'location', 'data_type']
        if os.path.exists(persistent_storage_root) is False or os.path.isdir(persistent_storage_root) is False:
             raise Exception(f"persistent_storage_root {persistent_storage_root} is not a directory.")
        self.persistent_storage_root = persistent_storage_root
        self.cluster=False
        self.default_record = None

    def set_default_record(self, default_record):
        if isinstance(default_record, str):
            filename = default_record
            try:
                with open(filename, "r") as f:
                    default_record = json.load(f)
            except Exception as e:
                raise Exception(f"Error while loading default_record from {filename}: {e}")
            if 'from_uuid4' not in default_record:
                default_record['from_uuid4'] = str(uuid.uuid4())
                with open(filename, "w") as f:
                    json.dump(default_record, f, indent=4)
        for field in self.schema:
            if field not in default_record:
                raise Exception(f"Default record {default_record} does not contain field {field}")
        self.default_record = default_record

    def _gen_filename(self, domain, utctime=None):
        if utctime is None:
            utctime = datetime.datetime.utcnow().replace(tzinfo=ZoneInfo('UTC')).isoformat()
        invalids = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '{', '}', '\n', '\r', ')', '(']
        fn=f"{utctime}_{self.default_record['from_uuid4']}.json"
        for invalid in invalids:
            fn = fn.replace(invalid, '_')
        fp=os.path.join(self.persistent_storage_root, domain)
        if not os.path.exists(fp):
            os.makedirs(fp)
        fn = os.path.join(fp, fn)
        return fn

    def _cluster_data_reset(self):
        self.cluster_ij = None
        self.current_cluster_date = None
        self.cluster_data = None
        self.cluster_data_type = None
        self.cluster_from_instance = None
        self.cluster_start = None
        self.cluster_end = None
        
    def _cluster_data_flush(self):
        if self.cluster_data is None or self.cluster_ij is None:
            return
        filename = self._gen_filename(self.cluster_ij['domain'], self.cluster_start)
        self.cluster_ij['data'] = self.cluster_data
        self.cluster_ij['time_end'] = self.cluster_end
        with open(filename, "w") as f:
            json.dump(self.cluster_ij, f) # , indent=4)
        self._cluster_data_reset()

    def _cluster_data_append(self, ij, data):
        cluster_date = ij['time'][:10]
        cluster_time = ij['time'][11:19]
        cluster_date_end = ij['time_end'][:10]
        cluster_time_end = ij['time_end'][11:19]
        if self.current_cluster_date == cluster_date and self.current_cluster_date == cluster_date_end and \
           self.cluster_data_type == ij['data_type'] and self.cluster_from_instance == ij['from_instance']:
            if self.cluster_data is None:
                self.cluster_data = []
                self.cluster_ij = ij
            self.cluster_end = ij['time_end']
            self.cluster_data.append((cluster_time, cluster_time_end, data))
        else:
            if self.cluster_data is None:
                self.cluster_data = []
                self.cluster_ij = ij
                self.cluster_start = ij['time']
                self.cluster_end = ij['time_end']
                self.cluster_data_type = ij['data_type']
                self.cluster_from_instance = ij['from_instance']
                self.current_cluster_date = cluster_date
                self.cluster_data.append((cluster_time, cluster_time_end, data))
            else:
                self._cluster_data_flush()
                self.cluster_data = []
                self.cluster_ij = ij
                self.cluster_start = ij['time']
                self.cluster_end = ij['time_end']
                self.cluster_data_type = ij['data_type']
                self.cluster_from_instance = ij['from_instance']
                self.current_cluster_date = cluster_date
                self.cluster_data.append((cluster_time, cluster_time_end, data))
            if cluster_date != cluster_date_end:
                self._cluster_data_flush()

    def _clustering(self, is_enabled=True):
        if is_enabled is False:
            if self.cluster is True:
                # Flush
                self._cluster_data_flush()
        else:
            if self.cluster is False:
                self._cluster_data_reset()
        self.cluster = is_enabled

    def cluster_open(self):
        self._clustering(True);

    def cluster_close(self):
        self._clustering(False);

    def set_data(self, data, datetime_with_any_timezone=None, datetime_with_any_timezone_end=None, domain=None, from_instance=None, data_type=None):
        if self.default_record is None:
            raise Exception("Default record is not set: use set_default_record()")
        ij = self.default_record.copy()
        if datetime_with_any_timezone is None:
            utcisotime = datetime.datetime.utcnow().replace(tzinfo=ZoneInfo('UTC')).isoformat()
        else:
            utcisotime = datetime_with_any_timezone.astimezone(ZoneInfo('UTC')).isoformat()
        if datetime_with_any_timezone_end is None:
            utcisotime_end = utcisotime
        else:
            utcisotime_end = datetime_with_any_timezone_end.astimezone(ZoneInfo('UTC')).isoformat()
        ij['time'] = utcisotime
        ij['time_end'] = utcisotime_end
        if domain is not None:
            ij['domain'] = domain
        if from_instance is not None:
            ij['from_instance'] = from_instance
        if data_type is not None:
            ij['data_type'] = data_type
        if self.cluster is True:
            # cluster
            self._cluster_data_append(ij, data)
        else:
            ij['data'] = data
            filename = self._gen_filename(ij['domain'], utcisotime)
            with open(filename, "w") as f:
                json.dump(ij, f, indent=4)

    def compile_dataframe(self, domain, columns, filter_start_iso_utctime=None, filter_end_ico_utctime=None):
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
                record = json.load(f)
            if filter_start_iso_utctime is not None and record['time_end'] < filter_start_iso_utctime:
                continue
            if filter_end_ico_utctime is not None and record['time'] > filter_end_ico_utctime:
                continue
            clustered = isinstance(record['data'], list)
            if clustered:
                if len(record['data'][0]) != 3:
                    raise Exception(f"Invalid cluster-format in data of {file}, record {record['data'][0]} should be a list of tuples (start, end, data)")
            if clustered is True:
                sample_data = record['data'][0][2]
            else:
                sample_data = record['data']
            for column in columns:
                if column not in record and column not in sample_data:
                    raise Exception(f"column {column} does not exist in data for domain {domain}")
            row0 = {column : record[column] for column in record if column in columns}
            if clustered is True:
                for row in record['data']:
                    start_time = row[0]+record['time'][11:]
                    end_time = row[1]+record['time_end'][11:]
                    row0['time'] = start_time
                    row0['time_end'] = end_time
                    row1 = {column : row[column] for column in row if column in columns}
                    rowf = row0 | row1
                    if df is None:
                        df = pd.DataFrame(rowf, index=['time'])
                    else:
                        df = df.append(rowf, ignore_index=True)
            else:
                row1 = {column : record['data'][column] for column in record['data'] if column in columns}
                row = row0 | row1
                if df is None:
                    df = pd.DataFrame(row, index=['time'])
                else:
                    df = df.append(row, ignore_index=True)
        return df


