import logging
import os
import asyncio
from zoneinfo import ZoneInfo
from datetime import datetime


class EventProcessor:
    def __init__(self, name, toml_data):
        self.log = logging.getLogger("IndraCSV")
        try:
            self.loglevel = toml_data[name]['loglevel'].upper()
        except Exception as e:
            self.loglevel = logging.INFO
            logging.error(f"Missing entry 'loglevel' in indrajala.toml section {name}: {e}")
        self.log.setLevel(self.loglevel)
        self.toml_data = toml_data
        self.name = name
        self.ev_store = {}
        self.current_date = None
        self.active = False
        try:
            if self.toml_data[self.name]['active'] is False:
                return
            if os.path.isdir(self.toml_data[self.name]['rootpath']) is False:
                self.log.error(f"{self.name}: Root directory {self.toml_data[self.name]['rootpath']} does not exist")
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
        msg = {'cmd': 'ping', 'time': datetime.now(tz=ZoneInfo('UTC')), 'topic': 'hello', 'msg': 'world', 'origin': self.name}
        # return {'topic': None, 'msg': None, 'origin': self.name}
        return msg

    def get_utc_date(self):
        return datetime.now(tz=ZoneInfo('UTC')).strftime("%Y-%m-%d")

    def flush_data(self, topic, date, data):
        filepath = os.path.join(self.toml_data[self.name]['rootpath'], topic)
        filename = date + '.csv'
        if os.path.isdir(filepath) is False:
            os.makedirs(filepath)
        fn = os.path.join(filepath, filename)
        if os.path.isfile(fn) is False:
            with open(fn, 'w') as f:
                f.write('time,uuid,msg\n')
        with open(fn, 'a') as f:
            for row in data:
                try:
                    f.write(row[0]+',' + row[1] + ',' + row[2] + '\n')
                except Exception as e:
                    self.log.error(f"Failed to serialize {data} to {fn}, {e}")
        return True

    async def put(self, msg):
        if self.active is False:
            return
        if 'time' in msg:
            if 'topic' in msg:
                date = self.get_utc_date()
                if msg['topic'] not in self.ev_store or date != self.current_date:
                    self.current_date = date
                    # XXX: if actual caching is used, flush here:
                    if msg['topic'] in self.ev_store and len(self.ev_store[msg['topic']]['data']) > 0:
                        if not self.flush_data(msg['topic'], self.ev_store[msg['topic']]['date'], self.flush_data(self.ev_store[msg['topic']]['data'])):
                            self.log.error(f"Flushing cache failed: {msg}")
                    self.ev_store[msg['topic']] = {'date': date, 'data': []}
                self.ev_store[msg['topic']]['data'].append((msg['time'], msg['uuid'], msg['msg']))
                if self.flush_data(msg['topic'], self.ev_store[msg['topic']]['date'], self.ev_store[msg['topic']]['data']):
                    self.ev_store[msg['topic']]['data'] = []
        return
