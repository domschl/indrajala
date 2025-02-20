import datetime
import math

IndraTimeInterval = tuple[float, float | None] | tuple[float]

class IndraTime:
    """Class for converting between different time representations

    The Indra libraries use Julian dates for representing time internally, as they are
    easy to work with and can represent any date in the distant past or future. This class
    provides methods for converting between Julian dates and other time representations,
    such as datetime objects, fractional years, and string times.
    """

    @staticmethod
    def datetime_to_julian(dt: datetime.datetime) -> float | None:
        """Convert datetime to Julian date

        Note: datetime object must have a timezone!
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
        return IndraTime.discrete_time_to_julian(
            year, month, day, hour, minute, second, microsecond
        )

    @staticmethod
    def discrete_time_to_julian_gregorian_extended(
        year: int,
        month: int,
        day: int,
        hour: int,
        minute: int,
        second: int,
        microsecond: int,
    ) -> float:
        """Convert (extended) Gregorian date to Julian date

        Note: this method assumed the validity of the Gregorian calendar for all dates,
        including those before 1582, which is not historically correct. In most cases,
        the method `discrete_time_to_julian` should be used instead.

        :param year: year
        :param month: month (1-12)
        :param day: day (1-31)
        :param hour: hour (0-23)
        :param minute: minute (0-59)
        :param second: second (0-59)
        :param microsecond: microsecond (0-999999)
        :return: float Julian date
        """
        if month <= 2:
            year -= 1
            month += 12
        A = int(year / 100)
        B = 2 - A + int(A / 4)
        jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524.5
        jd += hour / 24 + minute / 1440 + second / 86400 + microsecond / 86400000000
        return jd

    @staticmethod
    def julian_to_discrete_time(jd: float) -> tuple[int, int, int, int, int, int, int]:
        """Convert Julian date to discrete time tuple

        :param jd: Julian date
        :return: tuple of (year, month, day, hour, minute, second, microsecond)
        """
        jd = jd + 0.5
        Z = math.floor(jd)
        F = jd - Z
        if Z < 2299161:
            a = Z
        else:
            alpha = math.floor((Z - 1867216.25) / 36524.25)
            a = Z + 1 + alpha - math.floor(alpha / 4)
        B = a + 1524
        C = math.floor((B - 122.1) / 365.25)
        D = math.floor(365.25 * C)
        E = math.floor((B - D) / 30.6001)
        day = B - D - math.floor(30.6001 * E) + F
        if E < 14:
            month = E - 1
        else:
            month = E - 13
        if month > 2:
            year = C - 4716
        else:
            year = C - 4715
        hour = 24 * (jd - math.floor(jd))
        minute = 60 * (hour - math.floor(hour))
        second = 60 * (minute - math.floor(minute))
        microsecond = 1000000 * (second - math.floor(second))

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
    def discrete_time_to_julian(
        year: int,
        month: int,
        day: int,
        hour: int,
        minute: int,
        second: int,
        microsecond: int,
    ) -> float | None:
        """Convert discrete time to Julian date, assuming Julian calendar for time < 1582
        and Gregorian calendar otherwise

        Notes: The new Gregorian calendar was developed by Aloysius Lilius (about 1510 - 1576) and
        Christophorus Clavius (1537/38 - 1612). It was established by a papal bull of
        Pope Gregor XIII that Thursday, October 4th, 1582, should be followed by
        Friday, October 15th, 1582. This shifted the date of the vernal equinox to its proper date.
        (`More info <https://www.ptb.de/cms/en/ptb/fachabteilungen/abt4/fb-44/ag-441/realisation-of-legal-time-in-germany/gregorian-calendar.html>`)


        :param year: year
        :param month: month (1-12)
        :param day: day (1-31)
        :param hour: hour (0-23)
        :param minute: minute (0-59)
        :param second: second (0-59)
        :param microsecond: microsecond (0-999999)
        :return: float Julian date
        """
        # if year == 0:
        #     print(
        #         f"Bad date at discrete_time_to_julian(): {year}-{month:02}-{day:02} {hour:02}:{minute:02}:{second:02}.{microsecond:06}"
        #     )
        #     print(
        #         "There is no year 0 in julian calendar! Use discrete_time_to_julian_gregorian_extended for continuous use of extended Gregorian calendar."
        #     )
        # return None
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
    def julian_to_datetime(jd: float) -> datetime.datetime:
        """Convert Julian date to datetime

        Note: datetime is only valid for dates after 1 AD, and before 9999 AD!

        :param jd: Julian date
        :return: datetime
        """
        year, month, day, hour, minute, second, microsecond = (
            IndraTime.julian_to_discrete_time(jd)
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
    def fractional_year_to_datetime(fy: float) -> datetime.datetime:
        """Convert fractional year to datetime

        Note: datetime is only valid for dates after 1 AD, and before 9999 AD!

        Scientific decimal time is based on the definition that a “Julian year” is exactly 365.25 days long.

        These values, based on the Julian year, are most likely to be those used in astronomy and related
        sciences. Note however that in a Gregorian year, which takes into account the 100 vs. 400 leap year
        exception rule of the Gregorian calendar, is 365.2425 days (the average length of a year over a
        400–year cycle).

        This routines uses the Julian year definition, a year of 365.25 days, and is thus not Gregorian.

        See: `Wikipedia Decimal time <https://en.wikipedia.org/w/index.php?title=Decimal_time>`

        :param fy: fractional year, e.g. 2020.5
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
    def datetime_to_fractional_year(dt: datetime.datetime) -> float:
        """
        Convert datetime to fractional year

        This method uses the Julian year definition, a year of 365.25 days, see fractional_year_to_datetime
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
    def fractional_year_to_julian(fy: float) -> float | None:
        """Convert fractional year to Julian date

        Note: fracyear fy is well defined for dates before 1AD, which are not representable in datetime.

        :param fy: fractional year
        :return: Julian date
        """
        # convert fractional year to Julian date
        # 1 AD is JD 1721423.5
        # 1 year is 365.25 days
        # Use datetime_to_fractional_year() to convert datetime to fractional year for dates after 1 AD
        if fy < 1:
            jd = 1721423.5 + (fy - 1) * 365.25
        else:
            dt = IndraTime.fractional_year_to_datetime(fy)
            jd = IndraTime.datetime_to_julian(dt)
        return jd

    @staticmethod
    def julian_to_fractional_year(jd: float) -> float:
        """Convert Julian date to fractional year

        Note: fracyear fy is well defined for dates before 1AD,
        which are not representable in datetime.

        :param jd: Julian date
        :return: fractional year
        """
        # convert Julian date to fractional year
        # 1 AD is JD 1721423.5
        # 1 year is 365.25 days
        jd_yr1 = 1721423.5
        if jd < jd_yr1:
            fy = 1 + (jd - 1721423.5) / 365.25
        else:
            dt = IndraTime.julian_to_datetime(jd)
            fy = IndraTime.datetime_to_fractional_year(dt)
        return fy

    @staticmethod
    def string_time_to_julian(time_str: str) -> IndraTimeInterval | None:
        """Convert string time to Julian date

        Time can be interval or point in time, interval-separator is " - "
        A point in time is either "YYYY-MM-DD", "YYYY-MM", or "YYYY" or "YYYY BC" or
        "N kya BP" or "N BP". Valid prefices are "N kya BP", "N ka BP", "N kyr BP", "N ka",
        "N kyr", "N kya", "N BP", "N BC", "N AD", "N ma BP", "N ga BP", "N ma", "N ga".

        Examples for points in time: "2020-01-01", "2020-01", "2020", "2020 BC", "1000 BP", "1000 kya BP"
        Examples for intervals: "2020-01-01 - 2021-01-01", "2020-01 - 2021-01", "2020 - 2021",
        "2021 BC - 2020 BC", "1001 BP - 1000 BP", "1001 kya BP - 1000 kya BP"

        Note that intervals are <earlier date> - <later date>, and that the earlier date is
        the first date in the string, which is not always intuitive for BC and BP dates!

        :param time_str: string time
        :return: tuple of Julian dates, second is None if point in time
        """
        time_str = time_str.strip()
        time_str = time_str.lower()
        pts = time_str.split(" - ")
        results: IndraTimeInterval | None = None
        for point in pts:
            pt = point.strip()
            if pt.endswith(" ad"):
                pt = pt[:-3]
            jdt = None
            if pt.endswith(" ma bp") or pt.endswith(" ma"):
                ma = float(pt.split(" ")[0])
                year = int(1950 - ma * 1000000.0)
                month = 1
                day = 1
                hour = 0
                minute = 0
                second = 0
                microsecond = 0
                jdt = IndraTime.discrete_time_to_julian(
                    year, month, day, hour, minute, second, microsecond
                )
            elif pt.endswith(" ga bp") or pt.endswith(" ga"):
                ga = float(pt.split(" ")[0])
                year = int(1950 - ga * 1000000000.0)
                month = 1
                day = 1
                hour = 0
                minute = 0
                second = 0
                microsecond = 0
                jdt = IndraTime.discrete_time_to_julian(
                    year, month, day, hour, minute, second, microsecond
                )
            elif (
                pt.endswith(" kya bp")
                or pt.endswith(" ka bp")
                or pt.endswith(" kyr bp")
                or pt.endswith(" ka")
                or pt.endswith(" kyr")
                or pt.endswith(" kya")
            ):
                kya = float(pt.split(" ")[0])
                # Convert to Julian date
                # 1 kya BP is 1000 years before 1950
                # 1950 is JD 2433282.5
                # jdt = 2433282.5 - kya * 1000.0 * 365.25
                year = int(1950 - kya * 1000.0)
                month = 1
                day = 1
                hour = 0
                minute = 0
                second = 0
                microsecond = 0
                jdt = IndraTime.discrete_time_to_julian(
                    year, month, day, hour, minute, second, microsecond
                )
            elif pt.endswith(" bp"):
                bp = int(pt.split(" ")[0])
                # Convert to Julian date
                # 1950 is JD 2433282.5
                # jdt = 2433282.5 - bp * 365.25
                year = 1950 - bp
                month = 1
                day = 1
                hour = 0
                minute = 0
                second = 0
                microsecond = 0
                jdt = IndraTime.discrete_time_to_julian(
                    year, month, day, hour, minute, second, microsecond
                )
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
                jdt = IndraTime.discrete_time_to_julian(
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
                jdt = IndraTime.discrete_time_to_julian(
                    year, month, day, hour, minute, second, microsecond
                )
            if results is None:
                if jdt is None:
                    return None
                else:
                    results = (jdt,)
            else:
                results = (results[0], jdt)
        return results

    @staticmethod
    def julian_to_string_time(jd: float) -> str:
        """Convert Julian date to string time

        This converts arbitrary Julian dates to string time. Dates after 13000 BC are formatted as BC, or
        AD dates (ommitting the 'AD' postfix). Earlier dates are expressed as BP (before present), kya BP,
        Ma BP, Ga BP, or Ga BP. See `string_time_to_julian` for more information about the supported formats.

        Example output: "2020-01-01", "2020-01", "2020", "2020 BC", "1000 BP", "1000 kya BP"

        :param jd: Julian date
        :return: string time
        """
        if jd < 1721423.5:  # 1 AD
            # > 13000 BP? Use BC, else use BP, and if < 100000 BP use kya BP
            if jd > 1721423.5 - 13000 * 365.25:
                # BC
                year, month, day, _hour, _minute, _second, _microsecond = (
                    IndraTime.julian_to_discrete_time(jd)
                )
                # bc = int((1721423.5 - jd) / 365.25) + 1
                year = 1 - year
                return f"{year} BC"
            elif jd > 1721423.5 - 100000 * 365.25:
                # BP
                year, month, day, _hour, _minute, _second, _microsecond = (
                    IndraTime.julian_to_discrete_time(jd)
                )
                # if year < 0:
                #    year = year + 1
                bp = 1950 - year
                # bp = int((1721423.5 - jd) / 365.25)
                return f"{bp} BP"
            elif jd > 1721423.5 - 100000000 * 365.25:
                # kya BP
                year, month, day, _hour, _minute, _second, _microsecond = (
                    IndraTime.julian_to_discrete_time(jd)
                )
                # if year < 0:
                #     year = year + 1
                kya = round((1950 - year) / 1000.0, 2)
                # kya = int((1721423.5 - jd) / (1000 * 365.25))
                return f"{kya} kya BP"
            elif jd > 1721423.5 - 10000000000 * 365.25:
                # Ma BP
                year, month, day, _hour, _minute, _second, _microsecond = (
                    IndraTime.julian_to_discrete_time(jd)
                )
                # if year < 0:
                #     year = year + 1
                ma = round((1950 - year) / 1000000.0, 2)
                return f"{ma} Ma BP"
            else:
                # Ga BP
                year, month, day, _hour, _minute, _second, _microsecond = (
                    IndraTime.julian_to_discrete_time(jd)
                )
                # if year < 0:
                #    year = year + 1
                ma = round((1950 - year) / 1000000000.0, 3)
                return f"{ma} Ga BP"
        else:
            # AD
            # dt = IndraTime.julian_to_datetime(jd)
            year, month, day, _hour, _minute, _second, _microsecond = (
                IndraTime.julian_to_discrete_time(jd)
            )
            if month == 1 and day == 1 and year < 1900:
                return str(year)
            elif day == 1 and year < 1900:
                return f"{year}-{month:02}"
            else:
                return f"{year}-{month:02}-{day:02}"

    @staticmethod
    def julian_to_ISO(jd: float) -> str:
        """Convert Julian date to extended ISO 8601 string

        Note: length of year is not limited to 4 digits, below 1000 AD, shorted and longer years may be used.
        No leading zeros for years are used, and year may be negative. Only UTC time is supported.
        """
        year, month, day, hour, minute, second, microsecond = (
            IndraTime.julian_to_discrete_time(jd)
        )
        return f"{year}-{month:02}-{day:02}T{hour:02}:{minute:02}:{second:02}.{microsecond:06}Z"

    @staticmethod
    def ISO_to_julian(iso: str) -> float | None:
        """Convert extended ISO 8601 string to Julian date

        Year may be negative and longer or shorter than 4 digits. Only UTC time is supported.
        See `julian_to_ISO` for more information.
        """
        parts = iso.split("T")
        if len(parts) != 2:
            raise ValueError(f"Invalid ISO 8601 string: {iso}")
        if parts[1][-1] == "Z":
            parts[1] = parts[1][:-1]
        if "+" in parts[1] or "-" in parts[1]:
            raise ValueError(f"Only UTC time is supported: {iso}")
        if parts[1][-1] not in "0123456789":
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
        if len(parts) == 1:
            microsecond = 0
        else:
            microsecond = int(parts[1])
        return IndraTime.discrete_time_to_julian(
            year, month, day, hour, minute, second, microsecond
        )
