import asyncio
import os
import logging
from zoneinfo import ZoneInfo
from datetime import datetime

class EventProcessor:
    def __init__(self, name, main_logger, toml_data):
        self.log = main_logger # logging.getLogger("CSV")
        # self.log.setLevel(logging.DEBUG)
        #  self.msh = logging.StreamHandler()
        # self.msh.setLevel(logging.DEBUG)
        # self.formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
        # self.msh.setFormatter(self.formatter)
        # self.log.addHandler(self.msh)
        self.toml_data = toml_data
        self.name = name
        self.ev_store={}
        self.current_date = None
        self.active = False
        try:
            if self.toml_data[self.name]['active'] is False:
                return
            if os.path.isdir(self.toml_data[self.name]['rootpath']) is False:
                self.log.error(f"{self.name}: Root directory {self.toml_data[self.name]['root']} does not exist")
                return
        except Exception as e:
            self.log.error(f"{self.name}: {e}")
            return
        self.active = True

    def isActive(self):
        return self.active

    async def async_init(self, loop):
        if self.active is False:
            return []
        self.loop = loop
        return ['#']

    async def get(self):
        if self.active is False:
            return None
        await asyncio.sleep(60.0)
        msg = {'topic': 'hello', 'msg': 'world', 'origin': self.name}
        self.log.debug(f"{self.name}: Sending message {msg}")
        # return {'topic': None, 'msg': None, 'origin': self.name}
        return msg

    def get_utc_date(self):
        return datetime.now(tz=ZoneInfo('UTC')).strftime("%Y-%m-%d")

    def flush_data(self, filepath, filename, data):
        if os.path.isdir(filepath) is False:
            os.makedirs(filepath)
        fn=os.path.join(filepath, filename)
        if os.path.isfile(fn) is False:
            with open(fn, 'w') as f:
                f.write('time,msg\n')
        with open(fn, 'a') as f:
            for row in data:
                f.write(row[0]+',' + row[1] + '\n')
        return True
    async def put(self, msg):
        if self.active is False:
            return
        filename=str
        self.log.debug(f"{self.name}: Received message {msg}")
        if 'time' in msg:
            if 'topic' in msg:
                if msg['topic'] not in self.ev_store:
                    date = self.get_utc_date()
                    self.ev_store[msg['topic']] = {'date': date, 'data': []}
                self.ev_store[msg['topic']]['data'].append((msg['time'], msg['msg']))
                filepath = os.path.join(self.toml_data[self.name]['rootpath'], msg['topic'])
                filename = self.ev_store[msg['topic']]['date'] + '.csv'
                if (self.flush_data(filepath, filename, self.ev_store[msg['topic']]['data'])):
                    self.ev_store[msg['topic']]['data'] = []
        return
