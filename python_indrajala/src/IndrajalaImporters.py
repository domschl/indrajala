# Filename: {time}_{domain}_{uuid4}.json
import uuid
import os
import datetime
from zoneinfo import ZoneInfo
import pandas as pd
from bs4 import BeautifulSoup
import json

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
        if os.path.exists(self.source_dir) is False or os.path.isfile(self.source_dir) is False:
            raise Exception(f"source_dir {self.source_dir} does not exist.")
        self.ies = IndrajalaEventSource(config_file=config_file)

    def import_data(self):
        with open (self.source_dir, "r") as fp:
            soup = BeautifulSoup(fp, 'lxml')

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
                self.ies.set_data({'message': text, 'from_name': from_name, 'local_time': strtime}, dtlocal)

