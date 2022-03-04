import uuid
import os
import datetime
try:
    from zoneinfo import ZoneInfo
except:
    from backports.zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
import json
from lxml import etree
import re
import pandas as pd
import numpy as np

from Indrajala import Indrajala

# TODO: entity registry
# TODO: canonical data names

def load_import_config(config_file):
    with open(config_file) as f:
        config = json.load(f)
    if 'persistent_storage_root' not in config:
        raise Exception(f'persistent_storage_root not specified in config {config_file}')
    if 'import_path' not in config:
        raise Exception(f'import_path not specified in config {config_file}')
    if 'default_record' not in config:
        raise Exception(f'default_record not specified in config {config_file}')
    if 'from_uuid4' not in config['default_record']:
        config['default_record']['from_uuid4'] = str(uuid.uuid4())
        with open(config_file, "w") as f:
            json.dump(config, f, indent=4)
    return (config['persistent_storage_root'], config['import_path'], config['default_record'])

class TelegramImporter:
    def __init__(self, config_file):
        persistent_storage_root, import_path, default_record = load_import_config(config_file)
        self.indra = Indrajala(persistent_storage_root)
        self.indra.set_default_record(default_record)
        self.import_path = import_path

    def import_data(self):
        dirs = [name for name in os.listdir(self.import_path) if os.path.isdir(os.path.join(self.import_path, name))]
        for dir in dirs:
            path = os.path.join(self.import_path, dir)
            repl_token='{chat_id}'
            if repl_token in self.indra.default_record['domain']:
                domain = self.indra.default_record['domain'].replace(repl_token, dir)
            else:
                domain = self.indra.default_record['domain']

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
                                self.indra.set_data({'message': text, 'from_name': from_name, 'local_time': strtime}, 
                                                    datetime_with_any_timezone=dtlocal, domain=domain)

class AppleHealthImporter:
    def __init__(self, config_file):
        persistent_storage_root, import_path, default_record = load_import_config(config_file)
        self.indra = Indrajala(persistent_storage_root)
        self.indra.set_default_record(default_record)
        self.import_path = import_path
        self.field_names={'BodyMassIndex': 'body_mass_index','Height': 'height','BodyMass': 'body_mass','HeartRate': 'heart_rate',
                          'OxygenSaturation': 'oxygen_saturation','BloodPressureSystolic': 'blood_pressure_systolic',
                          'BloodPressureDiastolic': 'blood_pressure_diastolic','BodyTemperature': 'body_temperature',
                          'BodyFatPercentage': 'body_fat_percentage','LeanBodyMass': 'lean_body_mass','StepCount': 'step_count',
                          'DistanceWalkingRunning': 'distance_walking_running','BasalEnergyBurned': 'basal_energy_burned',
                          'ActiveEnergyBurned': 'active_energy_burned','FlightsClimbed': 'flights_climbed',
                          'AppleExerciseTime': 'apple_exercise_time','DistanceCycling': 'distance_cycling',
                          'DistanceSwimming': 'distance_swimming','SwimmingStrokeCount': 'swimming_stroke_count',
                          'RestingHeartRate': 'resting_heart_rate','VO2Max': 'vo2_max',
                          'WalkingHeartRateAverage': 'walking_heart_rate_average',
                          'EnvironmentalAudioExposure': 'environmental_audio_exposure',
                          'HeadphoneAudioExposure': 'headphone_audio_exposure',
                          'WalkingDoubleSupportPercentage': 'walking_double_support_percentage',
                          'SixMinuteWalkTestDistance': 'six_minute_walk_test_distance','AppleStandTime': 'apple_stand_time',
                          'WalkingSpeed': 'walking_speed','WalkingStepLength': 'walking_step_length',
                          'WalkingAsymmetryPercentage': 'walking_asymmetry_percentage','StairAscentSpeed': 'stair_ascent_speed',
                          'StairDescentSpeed': 'stair_descent_speed',
                          'AppleWalkingSteadiness': 'apple_walking_steadiness',
                          'HeartRateVariabilitySDNN': 'heart_rate_variability_sdnn',
                          # data types
                          'HKDataTypeSleepDurationGoal': 'data_type_sleep_duration_goal',
                          # category types
                          'HKCategoryTypeIdentifierSleepAnalysis': 'category_type_identifier_sleep_analysis',
                          'HKCategoryTypeIdentifierAppleStandHour': 'category_type_identifier_apple_stand_hour',
                          'HKCategoryTypeIdentifierMindfulSession': 'category_type_identifier_mindful_session',
                          'HKCategoryTypeIdentifierHandwashingEvent': 'category_type_identifier_handwashing_event',
                    }


        self.units={'bpm': ('hz', 'hz', lambda x: float(x)/60.0), 'count':('count', 'count', lambda x: float(x)), 
                    'kg':('g', 'g', lambda x: float(x)*1000.0), 'cm':('m', 'm', lambda x: float(x)/100.0),
                    'count/min':('hz', 'hz', lambda x: float(x)/60.0), '%':('%', '%', lambda x: float(x))}

    @staticmethod
    def _translate_source(source_name):
        # translate camelCase to snake_case
        source_name = ''.join(['_'+c.lower() if c>='A' and c<='Z' else c for c in source_name])[1:]
        invalids = ['.', '/', '\\', ' ', ':', '*', '?', '"', '<', '>', '|', '\n', '\r', "'"]
        for invalid in invalids:
            source_name = source_name.replace(invalid, '_')
        return source_name

    def _translate_type(self, type_name):
        if type_name not in self.field_names:
            raise Exception(f'unknown type {type_name}')
        return self.field_names[type_name]

    def _translate_unit(self, unit_name):
        if unit_name not in self.units:
            raise Exception(f'unknown unit {unit_name}')
        return self.units[unit_name][0]

    def _translate_value(self, value, from_unit):
        if from_unit not in self.units:
            raise Exception(f'unknown unit {from_unit} conversion requested for {value}')
        return self.units[from_unit][2](value)

    @staticmethod
    def _path_safe(name):
        invalids = ['.', '/', '\\', ' ', ':', '*', '?', '"', '<', '>', '|', '\n', '\r', "'"]
        for invalid in invalids:
            name = name.replace(invalid, '_')
        return name

    def import_data(self, max_data=None):
        n = 0
        expected_fields = ['type', 'sourceName', 'sourceVersion', 'unit', 'creationDate', 'startDate', 'endDate', 'value']
        optional_fields = {'value': 'Event'}  # Give a default value for optional fields.
        data_file = os.path.join(self.import_path, 'Export.xml')
        if os.path.exists(data_file) is False or os.path.isfile(data_file) is False:
            raise Exception(f"Apple Health data_file {data_file} does not exist.")
        self.indra.cluster_open()
        for _, element in etree.iterparse(data_file, tag='Record'):
            n += 1
            if max_data is not None and n > max_data:
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
            source = self._translate_source(d['sourceName'])
            dtype = self._translate_type(d['type'])
            if 'unit' in d:
                unit = d['unit']
                unit_path = self._path_safe(self._translate_unit(unit))
            else:
                unit_path = None
                unit = None
            domain = self.indra.default_record['domain'].replace('{data_type}', dtype)
            from_instance = self.indra.default_record['from_instance'].replace('{from_instance}', source)
            data_type = self.indra.default_record['data_type'].replace('{data_type}', dtype)
            if unit_path is not None and unit_path != '':
                data_type = data_type + '/'+unit_path
            self.indra.set_data(self._translate_value(data['value'], unit), datetime_with_any_timezone=dt, datetime_with_any_timezone_end=de, domain=domain,
                                from_instance=from_instance, data_type=data_type)
            element.clear(keep_tail=True)
        self.indra.cluster_close()

class GoogleContactsImporter():
    def __init__(self, config_file):
        persistent_storage_root, import_path, default_record = load_import_config(config_file)
        self.indra = Indrajala(persistent_storage_root)
        self.indra.set_default_record(default_record)
        self.import_path = import_path
        self.field_names={
                    }

    def import_data(self, address_book='All Contacts', max_data=None):
        data_path = os.path.join(self.import_path, address_book)
        filename = os.path.join(data_path, 'All Contacts.csv')
        if os.path.exists(filename) is False or os.path.isfile(filename) is False:
            raise Exception(f"Google Contacts data_file {filename} does not exist.")
        df = pd.read_csv(filename, sep=',', header=0, index_col=0)
        # df.replace('',np.nan)
        # dfc = df.dropna(how='all', axis='columns')
        # print(dfc.head())
        # 
        has_cont = []
        drops = []
        for col in df.columns.values.tolist():
            cont=False
            lst_cont = None
            for v in df[col].values.tolist():
                if v is not None and v != '' and v!=np.nan and str(v)!="nan":
                    cont=True
                    lst_cont = v
                    break
            if cont is False:
                print(f"Dropping column {col}")
                drops.append(col)
                # df.drop(col, axis=1, inplace=True)
            else:
                # print(f"Keeping column {col}, content {lst_cont}")
                pass

        dfc = df.drop(drops, axis=1)

        print(dfc.head())

        print(dfc.columns.values.tolist())

        attribs = {}

        analyse= ['Birthday', 'Name Prefix']

        print("-----------------------")

        for col in dfc.columns.values.tolist():
            # print(f"Column {col}")
            for v in df[col].values.tolist():
                if v is not None and v != '' and v!=np.nan and str(v)!="nan":
                    if col not in attribs:
                        attribs[col]={'count':0}
                    attribs[col]['count']+=1
                    if col in analyse:
                        print(f"{col}={v}")

        print(attribs)

        print("-----------------------")

        for index, row in dfc.iterrows():
            b=str(row['Birthday'])
            if b is not None and b != '' and b!=np.nan and str(b)!="nan":
                if b[:2]=='16':
                   print(f"Invalid year {b}")
                else:
                    dt = datetime.datetime.strptime(b, '%Y-%m-%d')
                    utctime=dt.replace(tzinfo=ZoneInfo('UTC')).isoformat()
                    print(f"i:[{index}] {dt} {utctime}")


        print("-----------------------")
        # pd.set_option('display.max_columns', None)
        n=0
        for index, row in dfc.iterrows():
            if str(index)=='nan':
                print()
                print(f"NAN:")
                for v in row.values.tolist():
                    if v is not None and v != '' and v!=np.nan and str(v)!="nan":
                        print(f"{v} ", end='')
                print()
                print()
            else:
                # print(f"i({n}):[{index}] ", end='')
                pass
            n+=1

        print("-----------------------")
        for index, row in dfc.iterrows():
            if str(index)!='nan':
                nn=index.split(' ')
                if len(nn)==2:
                    print(f"* {index}")
                else:
                    print(f"  -- {index}")

