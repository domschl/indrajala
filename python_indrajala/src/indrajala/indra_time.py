# import time
from asyncio.proactor_events import _ProactorBaseWritePipeTransport
import math
import re
from datetime import datetime
from zoneinfo import ZoneInfo


class IndraTime:
    def __init__(self):
        ''' Initialize IndraTime, the current time is the default value.

        Use one of the `set_*` functions to change.
        '''
        self.repr = "dt"
        self.dt = datetime.now(tz=ZoneInfo('UTC'))
        self.bp0 = datetime(1950, 1, 1, 0, 0, 0, tzinfo=ZoneInfo('UTC')).timestamp()
        self.dt0 = datetime(1, 1, 1, 0, 0, 0, tzinfo=ZoneInfo('UTC')).timestamp()
        self.year_solar_days = 365.24217  # WP: https://en.wikipedia.org/wiki/Tropical_year
        self.len_year = self.year_solar_days*24*3600
        self.set_max_bc_range(5000)

    def year2sec(self, yr):
        return yr*self.len_year

    def set_max_bc_range(self, bc_year=5000):
        self.max_bc_age = bc_year
        self.bc_max = self.dt0 - self.year2sec(self.max_bc_age)

    def set_datetime(self, dt):
        ''' Set IndraTime via a datetime'''
        self.repr = "dt"
        self.dt = dt

    def set_timestamp(self, t):
        ''' Set IndraTime via an UTC unix timestamp'''
        if t < self.dt0:
            self.repr = "it"
            self.it = t
        else:
            self.repr = "dt"
            self.dt = datetime.fromtimestamp(t).astimezone(ZoneInfo('UTC'))

    def set_bp(self, bp):
        ''' Set IndraTime via an 'Before Present' (BP) time in seconds as distance from 1950. '''
        ut = self.bp0 - bp
        if ut >= self.dt0:
            self.dt = datetime.fromtimestamp(ut).astimezone(ZoneInfo('UTC'))
            self.repr = 'dt'
            return self.dt
        else:
            self.it = ut
            self.repr = 'it'
            return self.it

    def set_ybp(self, ybp):
        ''' Set time as years before present (=1950).'''
        return self.set_bp(ybp*self.len_year)

    def set_ybc(self, ybc):
        ''' Set time as year BC '''
        self.it = (-1*(ybc-1)*self.len_year)+self.dt0
        return self.it

    def set_year_string(self, year_string):
        pass

    def get_bp(self):
        ''' seconds before present (BP), with present=1950-01-01 '''
        if self.repr == 'dt':
            self.it = self.dt.timestamp()
        bp = self.bp0 - self.it
        return bp

    def get_ybp(self, years_only=True):
        ''' years before present (BP), with present=1950-01-01 '''
        bp = self.get_bp()
        bpy = bp / self.len_year
        if years_only is True:
            bpy = math.trunc(bpy)
        return bpy

    def get_bc(self, years_only=True):
        ''' years BC, only valid for < AD 1 times! '''
        if self.repr == 'dt':
            return None  # Internal error!
        bc = -1 * (self.it-self.dt0)/self.len_year + 1
        if years_only is True:
            bc = math.trunc(bc)
        return bc

    def get_string(self, years_only=True, use_BC=True):
        ''' Get human readable rendering as ISO-Time, year BC, or year BP '''
        if self.repr == 'dt':
            return self.dt.isoformat()
        elif self.repr == 'it':
            if self.it < self.bc_max or use_BC is False:
                bpy = self.get_bpy(years_only=years_only)
                str_bp = f"{bpy:.0f} BP"
                return str_bp
            else:
                bc = self.get_bc(years_only=years_only)
                str_bc = f"{bc:.0f} BC"
                return str_bc
        else:
            return None

    def __str__(self):
        return self.get_string()
