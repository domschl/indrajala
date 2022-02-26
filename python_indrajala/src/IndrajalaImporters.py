# Filename: {time}_{domain}_{uuid4}.json
import uuid
import os
import datetime
from zoneinfo import ZoneInfo
import pandas as pd
from bs4 import BeautifulSoup
import json
from lxml import etree
from copy import copy

from Indrajala import IndrajalaEventSource, __SCHEMA__

def checkIndrajalaConfig(config, additional_fields=None):
    """
    Check if the config file exists and is valid
    """
    if isinstance(config, str):
        if os.path.exists(config) is False or os.path.isfile(config) is False:
            raise Exception(f"config_file {config} does not exist.")
        with open(config, "r") as f:
            config = json.load(f)
            if 'from_uuid4' not in config:
                config['from_uuid4'] = str(uuid.uuid4())
                with open(config, "w") as f:
                    json.dump(config, f, indent=4)
    required_fields = __SCHEMA__
    if additional_fields is not None:
        required_fields.extend(additional_fields)
    for field in required_fields:
        if field not in config:
            raise Exception(f"config_file {config} is missing field {field}")
    return config, IndrajalaEventSource(config=config)

class TelegramImporter:
    def __init__(self, config=None):
        self.config, self.ies = checkIndrajalaConfig(config=config, additional_fields=['source_dir'])

    def import_data(self):
        dirs = [name for name in os.listdir(self.config['source_dir']) if os.path.isdir(os.path.join(self.config['source_dir'], name))]
        for dir in dirs:
            path = os.path.join(self.config['source_dir'], dir)
            repl_token='{chat_id}'
            if repl_token in self.config['domain']:
                domain = self.config['domain'].replace(repl_token, dir)
            else:
                domain = self.config['domain']

            if repl_token in domain:
                print(f"{domain} contains {repl_token}")
                exit(-1)

            for file in os.listdir(path):
                if file.endswith(".html"):
                    import_file = os.path.join(path, file)
                    soup = None
                    with open (import_file, "r") as fp:
                        soup = BeautifulSoup(fp, 'lxml')
                    if soup is not None:
                        for message in soup.find_all('div', class_='body'):
                            time=message.find('div', class_='date')
                            if time is not None:
                                strtime=time['title'].strip()
                            else:
                                strtime=None
                            body=message.find('div', class_='text')
                            if body is not None:
                                text = body.text.strip()
                            else:
                                text=None
                            from_name=message.find('div', class_='from_name')
                            if from_name is not None:
                                from_name=from_name.text.strip()
                            else:
                                from_name=None
                            if strtime is not None and text is not None and from_name is not None:
                                print(f"{strtime} [{from_name}] {text[:50]}...")
                                dtime=datetime.datetime.strptime(strtime, '%d.%m.%Y %H:%M:%S')
                                dtlocal=dtime.astimezone()
                                self.ies.set_data({'message': text, 'from_name': from_name, 'local_time': strtime}, datetime_with_any_timezone=dtlocal, domain=domain)

class AppleHealthImporter:
    def __init__(self, config=None):
        self.config, self.ies = checkIndrajalaConfig(config=config, additional_fields=['source_dir'])

    def import_data(self):
        emergency_break = 10000
        n = 0
        expected_fields = ['type', 'sourceName', 'sourceVersion', 'unit', 'creationDate', 'startDate', 'endDate', 'value']
        optional_fields = {'value': 'Event'}  # Give a default value for optional fields.
        data_file = os.path.join(self.config['source_dir'], 'Export.xml')
        if os.path.exists(data_file) is False or os.path.isfile(data_file) is False:
            raise Exception(f"Apple Health data_file {data_file} does not exist.")
        current_cluster_date = None
        cluster_data = None
        cluster_type = None
        cluster_start = None
        cluster_end = None
        for _, element in etree.iterparse(data_file, tag='Record'):
            n += 1
            if n > emergency_break:
                break
            d=element.attrib
            ok=True
            for field in expected_fields:
                if field not in d:
                    print(f"Unexpected data record {d}, does not contain {field} - skipping.")
                    ok=False
            if ok is False:
                continue
            avail_fields=expected_fields.copy()
            for field in optional_fields.keys():
                if field not in d:
                    avail_fields.append(field)
                    d[field]=optional_fields[field]

            # Apple mess:  '2015-11-13 07:23:35 +0100'
            cluster_date = d['startDate'][:10]
            cluster_time = d['startDate'][11:19]
            dt= datetime.datetime.strptime(d['startDate'], '%Y-%m-%d %H:%M:%S %z')
            de= datetime.datetime.strptime(d['endDate'], '%Y-%m-%d %H:%M:%S %z')
            bloat = 'HKQuantityTypeIdentifier'
            if bloat in d['type']:
                d['type'] = d['type'].replace(bloat, '')
            if 'device' in d:
                devstr=d['device']
                dev={}
                ind=devstr.find('>, ')
                if ind>0:
                    devstr=devstr[ind+3:]
                devatts=devstr.split(', ')
                for att in devatts:
                    par=att.split(':')
                    if len(par)==2:
                        if par[1][-1]=='>':  # remove trailing > from object-marker
                            par[1]=par[1][:-1]
                        dev[par[0]]=par[1]
                for field in ['name', 'manufacturer', 'model', 'hardware', 'software']:
                    if field in dev:
                        d[field]=dev[field]
                        avail_fields.append(field)
                del d['device']
            data={}
            for field in avail_fields:
                data[field]=d[field]
            domain = self.config['domain'].replace('{data_type}', d['type'])
            if cluster_date == current_cluster_date and cluster_type == d['type']:
                if cluster_data is None:
                    cluster_data = []
                cluster_end = d['endDate']
                cluster_data.append((cluster_time, data['value']))
            else:
                if cluster_data is None:
                    cluster_data = []
                    cluster_start = d['startDate']
                    cluster_end = d['endDate']
                    cluster_type = d['type']
                    current_cluster_date = cluster_date
                    cluster_data.append((cluster_time, data['value']))
                else:
                    dt= datetime.datetime.strptime(cluster_start, '%Y-%m-%d %H:%M:%S %z')
                    de= datetime.datetime.strptime(cluster_end, '%Y-%m-%d %H:%M:%S %z')
                    print(f"Cluster-write {cluster_type} {cluster_start} - {cluster_end}: {cluster_data}")
                    data_wr=data.copy()
                    data_wr['value']=cluster_data
                    self.ies.set_data(data_wr, datetime_with_any_timezone=dt, datetime_with_any_timezone_end=de, domain=domain)
                    cluster_data = []
                    cluster_start = d['startDate']
                    cluster_end = d['endDate']
                    cluster_type = d['type']
                    current_cluster_date = cluster_date
                    cluster_data.append((cluster_time, data['value']))
            element.clear(keep_tail=True)
        if cluster_data is not None:
            print(f"Cluster-flush: {cluster_data}")
            dt= datetime.datetime.strptime(cluster_start, '%Y-%m-%d %H:%M:%S %z')
            de= datetime.datetime.strptime(cluster_end, '%Y-%m-%d %H:%M:%S %z')
            data['value'] = cluster_data
            self.ies.set_data(data, datetime_with_any_timezone=dt, datetime_with_any_timezone_end=de, domain=domain)

