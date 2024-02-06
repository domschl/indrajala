import json
import datetime
import uuid


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
        self.time_jd_start = self.datetime2julian(
            datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
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

    @staticmethod
    def datetime2julian(dt: datetime.datetime):
        """Convert datetime to Julian date

        Note: datetime must have a timezone!
        Should work over the entire range of datetime, starting with year 1.

        :param dt: datetime object
        :return: float Julian date
        """
        if dt.tzinfo is None:
            raise ValueError(f"datetime {dt} must have a timezone!")
        dt = dt.astimezone(datetime.timezone.utc)
        year = dt.year
        month = dt.month
        day = dt.day
        hour = dt.hour
        minute = dt.minute
        second = dt.second
        microsecond = dt.microsecond
        if month <= 2:
            year -= 1
            month += 12
        A = int(year / 100)
        B = 2 - A + int(A / 4)
        jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524.5
        jd += hour / 24 + minute / 1440 + second / 86400 + microsecond / 86400000000
        return jd

    @staticmethod
    def julian2datetime(jd):
        """Convert Julian date to datetime"""
        jd = jd + 0.5
        Z = int(jd)
        F = jd - Z
        if Z < 2299161:
            A = Z
        else:
            alpha = int((Z - 1867216.25) / 36524.25)
            A = Z + 1 + alpha - int(alpha / 4)
        B = A + 1524
        C = int((B - 122.1) / 365.25)
        D = int(365.25 * C)
        E = int((B - D) / 30.6001)
        day = B - D - int(30.6001 * E) + F
        if E < 14:
            month = E - 1
        else:
            month = E - 13
        if month > 2:
            year = C - 4716
        else:
            year = C - 4715
        hour = 24 * (jd - int(jd))
        minute = 60 * (hour - int(hour))
        second = 60 * (minute - int(minute))
        microsecond = 1000000 * (second - int(second))
        dt = datetime.datetime(
            year,
            month,
            int(day),
            int(hour),
            int(minute),
            int(second),
            int(microsecond),
            tzinfo=datetime.timezone.utc,
        )
        return dt

    @staticmethod
    def fracyear2datetime(fy):
        """Convert fractional year to datetime

        Scientific decimal time is based on the definition that a “Julian year” is exactly 365.25 days long.

        These values, based on the Julian year, are most likely to be those used in astronomy and related
        sciences. Note however that in a Gregorian year, which takes into account the 100 vs. 400 leap year
        exception rule of the Gregorian calendar, is 365.2425 days (the average length of a year over a
        400–year cycle).

        This routines uses the Julian year definition, a year of 365.25 days, and is thus not Gregorian.

        See: https://en.wikipedia.org/w/index.php?title=Decimal_time

        :param fy: fractional year
        :return: datetime
        """
        year = int(fy)
        rem = fy - year
        dt = datetime.datetime(
            year, 1, 1, tzinfo=datetime.timezone.utc
        )  #  XXX this is Gregorian! Fix.
        dt += datetime.timedelta(seconds=rem * 365.25 * 24 * 60 * 60)
        return dt

    @staticmethod
    def datetime2fracyear(dt):
        """
        Convert datetime to fractional year

        This method uses the Julian year definition, a year of 365.25 days, see \ref fracyear2datetime
        for further discussion.

        Note: naive datetime objects are not accepted, as they are ambiguous, please set a timezone.

        @param dt: datetime
        @return: fractional year
        """
        if dt.tzinfo is None:
            raise ValueError(f"datetime {dt} must have a timezone!")
        return dt.year + (
            dt
            - datetime.datetime(
                dt.year, 1, 1, tzinfo=datetime.timezone.utc
            )  # XXX this is Gregorian! Fix.
        ).total_seconds() / (365.25 * 24 * 60 * 60)

    @staticmethod
    def fracyear2julian(fy):
        """Convert fractional year to Julian date

        Note: fracyear fy is well defined for dates before 1AD, which are not representable in datetime.

        :param fy: fractional year
        :return: Julian date
        """
        # Do not use datetime or fracyear2datetime!
        year = int(fy)
        rem = fy - year
        # no datetime!
