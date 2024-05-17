"use strict";


export class IndraTime {
    time_to_julian_gregorian(year, month, day, hour, minute, second, microsecond) {
        let a = Math.floor((14 - month) / 12);
        let y = year + 4800 - a;
        let m = month + 12 * a - 3;
        let jd = day + Math.floor((153 * m + 2) / 5) + 365 * y + Math.floor(y / 4) - Math.floor(y / 100) + Math.floor(y / 400) - 32045;
        let jd_frac = (hour - 12) / 24 + minute / 1440 + second / 86400 + microsecond / 86400000000;
        return jd + jd_frac;
    }

    julian_to_time(jd) {
        let z = Math.floor(jd + 0.5);
        let f = jd + 0.5 - z;
        let a = z;
        if (z < 2299161) {
            a = z;
        } else {
            let alpha = Math.floor((z - 1867216.25) / 36524.25);
            a = z + 1 + alpha - Math.floor(alpha / 4);
        }
        let b = a + 1524;
        let c = Math.floor((b - 122.1) / 365.25);
        let d = Math.floor(365.25 * c);
        let e = Math.floor((b - d) / 30.6001);
        let day = b - d - Math.floor(30.6001 * e) + f;
        let month = e - (e < 13.5 ? 1 : 13);
        let year = c - (month > 2.5 ? 4716 : 4715);
        let hour = Math.floor((day - Math.floor(day)) * 24);
        let minute = Math.floor(((day - Math.floor(day)) * 24 - hour) * 60);
        let second = Math.floor((((day - Math.floor(day)) * 24 - hour) * 60 - minute) * 60);
        let microsecond = Math.floor(((((day - Math.floor(day)) * 24 - hour) * 60 - minute) * 60 - second) * 1000000);
        return [year, month, Math.floor(day), hour, minute, second, microsecond];
    }

    time_to_julian(year, month, day, hour, minute, second, microsecond) {
        if (year == 0) {
            print("There is no year 0 in the Gregorian calendar.");
            return null;
        }
        if (year == 1582 && month == 10 && day > 4 && day < 15) {
            print("The Gregorian calendar was not in effect in this period.");
            return null;
        }
        let jy;
        let jm;
        if (month > 2) {
            jy = year;
            jm = month + 1;
        } else {
            jy = year - 1;
            jm = month + 13;
        }
        let intgr = Math.floor(Math.floor(365.25 * jy) + Math.floor(30.6001 * jm) + day + 1720995);
        let gregcal = 15 + 31 * (10 + 12 * 1582);
        if (day + 31 * (month + 12 * year) >= gregcal) {
            let ja = Math.floor(0.01 * jy);
            intgr += 2 - ja + Math.floor(0.25 * ja);
        }
        let dayfrac = (hour / 24) - 0.5;
        if (dayfrac < 0.0) {
            dayfrac += 1.0;
            --intgr;
        }
        let frac = dayfrac + (minute + second / 60.0 + microsecond / 1.0e6) / 60.0 / 24.0;
        let jd0 = ((intgr + frac) - 0.5) * 100000;
        let jd = Math.floor(jd0);
        if (jd0 - jd > 0.5) {
            jd += 1;
        }
        jd = jd / 100000;
        jd += microsecond / 86400000000;
        return jd;
    }

    // create JS Date object from Julian date
    julian_to_datetime(jd) {
        let [year, month, day, hour, minute, second, microsecond] = this.julian_to_time(jd);
        return new Date(year, month - 1, day, hour, minute, second, microsecond / 1000);
    }

    // create Julian date from JS Date object
    datetime_to_julian(dt) {
        return this.time_to_julian(dt.getFullYear(), dt.getMonth() + 1, dt.getDate(), dt.getHours(), dt.getMinutes(), dt.getSeconds(), dt.getMilliseconds() * 1000);
    }
}