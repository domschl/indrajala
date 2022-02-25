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

from Indrajala import IndrajalaEventSource

class TelegramImporter:
    def __init__(self, config_file=None):
        if os.path.exists(config_file) is False or os.path.isfile(config_file) is False:
            raise Exception(f"config_file {config_file} does not exist.")
        with open(config_file, "r") as f:
            config = json.load(f)
            if 'from_uuid4' not in config:
                config['from_uuid4'] = str(uuid.uuid4())
                with open(config_file, "w") as f:
                    json.dump(config, f, indent=4)
        self.config = config
        if 'source_dir' not in config:
            raise Exception(f"config_file {config_file} does not contain 'source_dir'.")
        else:
            self.source_dir = config['source_dir']
        if os.path.exists(self.source_dir) is False or os.path.isdir(self.source_dir) is False:
            raise Exception(f"source_dir {self.source_dir} is not a directory.")
        self.ies = IndrajalaEventSource(config_file=config_file)

    def import_data(self):
        dirs = [name for name in os.listdir(self.source_dir) if os.path.isdir(os.path.join(self.source_dir, name))]
        for dir in dirs:
            path = os.path.join(self.source_dir, dir)
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
    def __init__(self, config_file=None):
        if os.path.exists(config_file) is False or os.path.isfile(config_file) is False:
            raise Exception(f"config_file {config_file} does not exist.")
        with open(config_file, "r") as f:
            config = json.load(f)
            if 'from_uuid4' not in config:
                config['from_uuid4'] = str(uuid.uuid4())
                with open(config_file, "w") as f:
                    json.dump(config, f, indent=4)
        self.config = config
        if 'source_dir' not in config:
            raise Exception(f"config_file {config_file} does not contain 'source_dir'.")
        else:
            self.source_dir = config['source_dir']
        if os.path.exists(self.source_dir) is False or os.path.isdir(self.source_dir) is False:
            raise Exception(f"source_dir {self.source_dir} is not a directory.")
        if 'domain' not in config:
            raise Exception(f"config_file {config_file} does not contain 'domain'.")
        else:
            if '{data_type}' not in config['domain']:
                raise Exception(f"config_file {config_file} does not contain token '{{data_type}}' in 'domain': {config['domain']}.")
        self.ies = IndrajalaEventSource(config_file=config_file)

    def import_data(self):
        expected_fields = ['type', 'sourceName', 'sourceVersion', 'unit', 'creationDate', 'startDate', 'endDate', 'value']
        data_file = os.path.join(self.source_dir, 'Export.xml')
        if os.path.exists(data_file) is False or os.path.isfile(data_file) is False:
            raise Exception(f"Apple Health data_file {data_file} does not exist.")
        for _, element in etree.iterparse(data_file, tag='Record'):
            d=element.attrib
            ok=True
            for field in expected_fields:
                if field not in d:
                    print(f"Unexpected data record {d}, does not contain {field} - skipping.")
                    ok=False
            if ok is False:
                continue
            avail_fields=expected_fields.copy()

            # Apple mess:  '2015-11-13 07:23:35 +0100'
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
            self.ies.set_data(data, datetime_with_any_timezone=dt, datetime_with_any_timezone_end=de, domain=domain)
            element.clear(keep_tail=True)

