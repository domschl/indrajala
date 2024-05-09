import json
import datetime
import uuid
from indralib.indra_time import IndraTime


# XXX  https://en.wikipedia.org/wiki/Decimal_time
class IndraEvent:
    def __init__(self):
        """Create an IndraEvent json object

        :param domain:        MQTT-like path
        :param from_id:       originator-path, used for replies in transaction-mode
        :param uuid4:         unique id, is unchanged over transactions, can thus be used as correlator
        :paran parent_uuid4:  uui4 of (optional) parent event
        :param seq_no:        sequence number, can be used to order events and cluster sync
        :param to_scope:      session scope as domain hierarchy, identifies sessions or groups, can imply security scope or context
        :param time_jd_start:    event time as float julian date
        :param data_type      short descriptor-path
        :param data           JSON data (note: simple values are valid)
        :param auth_hash:     security auth (optional)
        :param time_jd_end:      end-of-event jd (optional)
        """
        self.domain = ""
        self.from_id = ""
        self.uuid4 = str(uuid.uuid4())
        self.parent_uuid4 = ""
        self.seq_no = 0
        self.to_scope = ""
        self.time_jd_start = IndraTime.datetime2julian(
            datetime.datetime.now(tz=datetime.timezone.utc)
        )
        self.data_type = ""
        self.data = ""
        self.auth_hash = ""
        self.time_jd_end = None

    def version(self):
        return "02"

    def old_versions(self):
        return ["", "01"]

    def to_dict(self):
        return self.__dict__

    def to_json(self):
        """Convert to JSON string"""
        return json.dumps(self.__dict__)

    @staticmethod
    def from_json(json_str):
        """Convert from JSON string"""
        ie = IndraEvent()
        ie.__dict__ = json.loads(json_str)
        return ie

    @staticmethod
    def mqcmp(pub, sub):
        """MQTT-style wildcard compare"""
        for c in ["+", "#"]:
            if pub.find(c) != -1:
                print(f"Illegal char '{c}' in pub in mqcmp!")
                return False
        inds = 0
        wcs = False
        for indp in range(len(pub)):
            if wcs is True:
                if pub[indp] == "/":
                    inds += 1
                    wcs = False
                continue
            if inds >= len(sub):
                return False
            if pub[indp] == sub[inds]:
                inds += 1
                continue
            if sub[inds] == "#":
                return True
            if sub[inds] == "+":
                wcs = True
                inds += 1
                continue
            if pub[indp] != sub[inds]:
                # print(f"{pub[indp:]} {sub[inds:]}")
                return False
        if len(sub[inds:]) == 0:
            return True
        if len(sub[inds:]) == 1:
            if sub[inds] == "+" or sub[inds] == "#":
                return True
        return False

    # @staticmethod
    # def datetime2julian(dt: datetime.datetime):
    #     return IndraTime.datetime2julian(dt)

    # @staticmethod
    # def julian2datetime(jd):
    #     return IndraTime.julian2datetime(jd)
