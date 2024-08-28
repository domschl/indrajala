import datetime
import math


class IndraTime:
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
        return IndraTime.time_to_julian(
            year, month, day, hour, minute, second, microsecond
        )

    @staticmethod
    def time_to_julian_gregorian(year, month, day, hour, minute, second, microsecond):
        # Convert (extended) Gregorian date to Julian date
        if month <= 2:
            year -= 1
            month += 12
        A = int(year / 100)
        B = 2 - A + int(A / 4)
        jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524.5
        jd += hour / 24 + minute / 1440 + second / 86400 + microsecond / 86400000000
        return jd

    @staticmethod
    def julian_to_time(jd):
        """Convert Julian date to discrete time"""
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

        # if year < 0:  ## XXX VERIFY!
        #     year -= 1

        return (
            year,
            month,
            int(day),
            int(hour),
            int(minute),
            int(second),
            int(microsecond),
        )

    @staticmethod
    def time_to_julian(year, month, day, hour, minute, second, microsecond):
        """Convert discrete time to Julian date, assume Julian calendar for time < 1582 otherwise Gregorian calendar"""
        # if year == 0:
        #     print(
        #         f"Bad date at time_to_julian(): {year}-{month:02}-{day:02} {hour:02}:{minute:02}:{second:02}.{microsecond:06}"
        #     )
        #     print(
        #         "There is no year 0 in julian calendar! Use time_to_julian_gregorian for continuous use of extended Gregorian calendar."
        #     )
        # return None
        # The new calendar was developed by Aloysius Lilius (about 1510 - 1576) and Christophorus Clavius (1537/38 - 1612).
        # It was established by a papal bull of Pope Gregor XIII that Thursday, October 4th, 1582, should be followed by Friday, October 15th, 1582.
        # This shifted the date of the vernal equinox to its proper date.
        # (https://www.ptb.de/cms/en/ptb/fachabteilungen/abt4/fb-44/ag-441/realisation-of-legal-time-in-germany/gregorian-calendar.html)
        if year == 1582 and month == 10 and day > 4 and day < 15:
            print(
                "The dates 5 - 14 Oct 1582 do not exist in the Gregorian calendar! Use to_time_gd for continuous juse of extended Gregorian calendar."
            )
            return None

        if month > 2:
            jy = year
            jm = month + 1
        else:
            jy = year - 1
            jm = month + 13

        intgr = math.floor(
            math.floor(365.25 * jy) + math.floor(30.6001 * jm) + day + 1720995
        )

        # check for switch to Gregorian calendar
        gregcal = 15 + 31 * (10 + 12 * 1582)
        if day + 31 * (month + 12 * year) >= gregcal:
            ja = math.floor(0.01 * jy)
            intgr += 2 - ja + math.floor(0.25 * ja)

        # correct for half-day offset
        dayfrac = hour / 24.0 - 0.5
        if dayfrac < 0.0:
            dayfrac += 1.0
            intgr -= 1

        # now set the fraction of a day
        frac = dayfrac + (minute + second / 60.0) / 60.0 / 24.0

        # round to nearest second XXX maybe not?
        jd0 = (intgr + frac) * 100000
        jd = math.floor(jd0)
        if jd0 - jd > 0.5:
            jd += 1
        jd = jd / 100000

        # add microsecond
        jd += microsecond / 86400000000

        return jd

    @staticmethod
    def julian2datetime(jd):
        """Convert Julian date to datetime"""
        year, month, day, hour, minute, second, microsecond = IndraTime.julian_to_time(
            jd
        )
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

    @staticmethod
    def string_time_2_julian(time_str):
        """Convert string time to Julian date

        Time can be interval or point in time, interval-separator is " - "
        A point in time is either "YYYY-MM-DD", "YYYY-MM", or "YYYY" or "YYYY BC" or
        "N kya BP" or "N BP"

        :param time_str: string time
        :return: tuple of Julian dates, second is None if point in time
        """
        time_str = time_str.strip()
        time_str = time_str.lower()
        pts = time_str.split(" - ")
        results = []
        for point in pts:
            pt = point.strip()
            if pt.endswith(" ad"):
                pt = pt[:-3]
            jdt = None
            if (
                pt.endswith(" kya bp")
                or pt.endswith(" kyr bp")
                or pt.endswith(" kyr")
                or pt.endswith(" kya")
            ):
                kya = float(pt.split(" ")[0])
                # Convert to Julian date
                # 1 kya BP is 1000 years before 1950
                # 1950 is JD 2433282.5
                jdt = 2433282.5 - kya * 1000.0 * 365.25
            elif pt.endswith(" bp"):
                bp = int(pt.split(" ")[0])
                # Convert to Julian date
                # 1950 is JD 2433282.5
                jdt = 2433282.5 - bp * 365.25
            elif pt.endswith(" bc"):
                # Convert to Julian date
                # 1 BC is 1 year before 1 AD
                # 1 AD is JD 1721423.5
                # old-year-only:bc = int(pt.split(" ")[0])
                # old-year-only: jdt = 1721423.5 - bc * 365.25
                hour = 0
                minute = 0
                second = 0
                microsecond = 0
                month = 1
                day = 1
                dts = pt[:-3].split("-")
                if len(dts) == 1:
                    # Year
                    try:
                        year = -1 * int(dts[0]) + 1
                    except ValueError:
                        raise ValueError(f"Invalid date format: {pt}")
                elif len(dts) == 2:
                    # Year and month
                    try:
                        year = -1 * int(dts[0]) + 1
                        month = int(dts[1])
                    except ValueError:
                        raise ValueError(f"Invalid date format: {pt}")
                elif len(dts) == 3:
                    # Year, month, and day
                    try:
                        year = -1 * int(dts[0]) + 1
                        month = int(dts[1])
                        day = int(dts[2])
                    except ValueError:
                        raise ValueError(f"Invalid date format: {pt}")
                else:
                    raise ValueError(f"Invalid date format: {pt}")
                jdt = IndraTime.time_to_julian(
                    year, month, day, hour, minute, second, microsecond
                )
            else:
                hour = 0
                minute = 0
                second = 0
                microsecond = 0
                month = 1
                day = 1
                dts = pt.split("-")
                if len(dts) == 1:
                    # Year
                    try:
                        year = int(dts[0])
                    except ValueError:
                        raise ValueError(f"Invalid date format: {pt}")
                elif len(dts) == 2:
                    # Year and month
                    try:
                        year = int(dts[0])
                        month = int(dts[1])
                    except ValueError:
                        raise ValueError(f"Invalid date format: {pt}")
                elif len(dts) == 3:
                    # Year, month, and day
                    try:
                        year = int(dts[0])
                        month = int(dts[1])
                        day = int(dts[2])
                    except ValueError:
                        raise ValueError(f"Invalid date format: {pt}")
                else:
                    raise ValueError(f"Invalid date format: {pt}")
                jdt = IndraTime.time_to_julian(
                    year, month, day, hour, minute, second, microsecond
                )
            results.append(jdt)
        return tuple(results)

    @staticmethod
    def julian_2_string_time(jd):
        """Convert Julian date to string time

        this uses datetime for 1 AD and later,
        and BC dates between 1 AD and 13000 BP and BP or kya BP dates for older

        :param jd: Julian date
        :return: string time
        """
        if jd < 1721423.5:  # 1 AD
            # > 13000 BP? Use BC, else use BP, and if < 100000 BP use kya BP
            if jd > 1721423.5 - 13000 * 365.25:
                # BC
                year, month, day, hour, minute, second, microsecond = (
                    IndraTime.julian_to_time(jd)
                )
                # bc = int((1721423.5 - jd) / 365.25) + 1
                year = 1 - year
                return f"{year} BC"
            elif jd > 1721423.5 - 100000 * 365.25:
                # BP
                bp = int((1721423.5 - jd) / 365.25)
                return f"{bp} BP"
            else:
                # kya BP
                kya = int((1721423.5 - jd) / (1000 * 365.25))
                return f"{kya} kya BP"
        else:
            # AD
            # dt = IndraTime.julian2datetime(jd)
            year, month, day, hour, minute, second, microsecond = (
                IndraTime.julian_to_time(jd)
            )
            if month == 1 and day == 1 and year < 1900:
                return str(year)
            elif day == 1 and year < 1900:
                return f"{year}-{month:02}"
            else:
                return f"{year}-{month:02}-{day:02}"

    @staticmethod
    def julian2ISO(jd):
        """Convert Julian date to extended ISO 8601 string

        Note: length of year is not limited to 4 digits, below 1000 AD, shorted and longer years may be used. No leading zeros are used, and year may be negative.
        """
        year, month, day, hour, minute, second, microsecond = IndraTime.julian_to_time(
            jd
        )
        return f"{year}-{month:02}-{day:02}T{hour:02}:{minute:02}:{second:02}.{microsecond:06}Z"

    @staticmethod
    def ISO2julian(iso):
        """Convert extended ISO 8601 string to Julian date
        Year may be negative and longer or shorter than 4 digits. Only UTC time is supported.
        """
        parts = iso.split("T")
        if len(parts) != 2:
            raise ValueError(f"Invalid ISO 8601 string: {iso}")
        date = parts[0]
        time = parts[1]
        if date[0] == "-":
            parts = date[1:].split("-")
            parts[0] = "-" + parts[0]
        else:
            parts = date.split("-")
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
        parts = time.split(":")
        hour = int(parts[0])
        minute = int(parts[1])
        parts = parts[2].split(".")
        second = int(parts[0])
        microsecond = int(parts[1][:-1])
        # if microsecond == None:
        #     microsecond = 0
        return IndraTime.time_to_julian(
            year, month, day, hour, minute, second, microsecond
        )
