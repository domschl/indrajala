"use strict";


/**
 * Class representing IndraTime utilities.
 * @class
 */
export class IndraTime {
    /**
     * Converts a given date and time to Julian date using the extended Gregorian calendar.
     * 
     * Note: the extended Gregorian calendar is a proleptic Gregorian calendar that extends 
     * the Gregorian calendar to dates before its introduction in 1582. In most cases, the
     * Julian calendar is used for dates before 1582, for this see the discreteTimeToJulian function.
     * 
     * @param {number} year - The year.
     * @param {number} month - The month (1-12).
     * @param {number} day - The day (1-31).
     * @param {number} hour - The hour (0-23).
     * @param {number} minute - The minute (0-59).
     * @param {number} second - The second (0-59).
     * @param {number} microsecond - The microsecond (0-999999).
     * @returns {number} The Julian date.
     * @example
     * let julianDate = IndraTime.discreteTimeToJulianGregorianExtended(2023, 10, 5, 12, 0, 0, 0);
     * console.log(julianDate);
     * @see discreteTimeToJulian
     */
    static discreteTimeToJulianGregorianExtended(year, month, day, hour, minute, second, microsecond) {
        let a = Math.floor((14 - month) / 12);
        let y = year + 4800 - a;
        let m = month + 12 * a - 3;
        let jd = day + Math.floor((153 * m + 2) / 5) + 365 * y + Math.floor(y / 4) - Math.floor(y / 100) + Math.floor(y / 400) - 32045;
        let jd_frac = (hour - 12) / 24 + minute / 1440 + second / 86400 + microsecond / 86400000000;
        return jd + jd_frac;
    }

    static julianToDiscreteTime(jd) {
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

    static discreteTimeToJulian(year, month, day, hour, minute, second, microsecond) {
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
        let dayfrac = (hour / 24.0) - 0.5;
        if (dayfrac < 0.0) {
            dayfrac += 1.0;
            --intgr;
        }
        let frac = dayfrac + (minute + second / 60.0) / 60.0 / 24.0;
        let jd0 = (intgr + frac) * 100000;
        let jd = Math.floor(jd0);
        if (jd0 - jd > 0.5) {
            jd += 1;
        }
        jd = jd / 100000;
        jd += microsecond / 86400000000;
        return jd;
    }

    // create JS Date object from Julian date
    static julianToDatetime(jd) {
        let [year, month, day, hour, minute, second, microsecond] = this.julianToDiscreteTime(jd);
        let dtutc = Date.UTC(year, month - 1, day, hour, minute, second, microsecond / 1000);
        return new Date(dtutc);
    }

    // create Julian date from JS Date object
    static datetimeToJulian(dt) {
        return this.discreteTimeToJulian(dt.getUTCFullYear(), dt.getUTCMonth() + 1, dt.getUTCDate(), dt.getUTCHours(), dt.getUTCMinutes(), dt.getUTCSeconds(), dt.getUTCMilliseconds() * 1000);
    }

    static datetimeNowToJulian() {
        //UTC time!
        let dt = new Date();
        return this.discreteTimeToJulian(dt.getUTCFullYear(), dt.getUTCMonth() + 1, dt.getUTCDate(), dt.getUTCHours(), dt.getUTCMinutes(), dt.getUTCSeconds(), dt.getUTCMilliseconds() * 1000);
    }

    static julianToISO(jd) {
        let [year, month, day, hour, minute, second, microsecond] = IndraTime.julianToDiscreteTime(jd);
        return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}T${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}:${String(second).padStart(2, '0')}.${String(microsecond).padStart(6, '0')}Z`;
    }

    static ISOTojulian(iso) {
        // Only UTC time is supported!
        let parts = iso.split("T");
        if (parts.length < 2) {
            print(`Invalid ISO 8601 string: ${iso}`);
            return null;
        }
        let date = parts[0]
        let time = parts[1]
        if (date[0] == '-') {
            parts = date.substring(1).split("-");
            parts[0] = "-" + parts[0];
        } else {
            parts = date.split("-");
        }
        let year = parseInt(parts[0]);
        let month = parseInt(parts[1]);
        let day = parseInt(parts[2]);
        parts = time.split(":");
        let hour = parseInt(parts[0]);
        let minute = parseInt(parts[1]);
        parts = parts[2].split(".");
        let second = parseInt(parts[0]);
        let microsecond = parseInt(parts[1].substring(0, parts[1].length - 1));
        return this.discreteTimeToJulian(year, month, day, hour, minute, second, microsecond);
    }

    static julianToStringTime(jd) {
        if (jd < 1721423.5) {  // 1 AD
            if (jd > 1721423.5 - 13000 * 365.25) {
                // BC
                let [year, month, day, hour, minute, second, microsecond] = IndraTime.julianToDiscreteTime(jd);
                year = 1 - year;
                return `${year} BC`;
            } else if (jd > 1721423.5 - 100000 * 365.25) {
                // BP
                let bp = Math.floor((1721423.5 - jd) / 365.25);
                return `${bp} BP`;
            } else {
                // kya BP
                let kya = Math.floor((1721423.5 - jd) / (1000 * 365.25));
                return `${kya} kya BP`;
            }
        } else {
            // AD
            let [year, month, day, hour, minute, second, microsecond] = IndraTime.julianToDiscreteTime(jd);
            if (month === 1 && day === 1 && year < 1900) {
                return `${year}`;
            } else if (day === 1 && year < 1900) {
                return `${year}-${month.toString().padStart(2, '0')}`;
            } else {
                return `${year}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
            }
        }
    }

    static stringTimeToJulian(timeStr) {
        timeStr = timeStr.trim();
        // lower case
        timeStr = timeStr.toLowerCase();
        let pts = timeStr.split(" - ");
        let results = [];
        for (let point of pts) {
            let pt = point.trim();
            if (pt.endsWith(" ad")) {
                pt = pt.substring(0, pt.length - 3);
            }
            let jdt = null;
            if (pt.endsWith(" kya bp") || pt.endsWith(" kyr bp") || pt.endsWith(" kyr") || pt.endsWith(" kya")) {
                let kya = parseInt(pt.split(" ")[0]);
                jdt = 2433282.5 - kya * 1000.0 * 365.25;
            } else if (pt.endsWith(" bp")) {
                let bp = parseInt(pt.split(" ")[0]);
                jdt = 2433282.5 - bp * 365.25;
            } else if (pt.endsWith(" bc")) {
                let bc = parseInt(pt.split(" ")[0]);
                jdt = 1721423.5 - bc * 365.25;
            } else {
                let hour = 0;
                let minute = 0;
                let second = 0;
                let microsecond = 0;
                if ("t" in pt) {
                    pti = pt.split("t");
                    pt = pti[0];
                    if (pti.length > 1) {
                        ptt = pti[1];
                        let tts = ptt.split(":");
                        if (tts.length === 1) {
                            hour = parseInt(tts[0]);
                        } else if (tts.length === 2) {
                            hour = parseInt(tts[0]);
                            minute = parseInt(tts[1]);
                        } else if (tts.length === 3) {
                            hour = parseInt(tts[0]);
                            minute = parseInt(tts[1]);
                            second = parseInt(tts[2]);
                        }
                        if (hour < 0 || hour >= 24) {
                            hour = 0;
                        }
                        if (minute < 0 || minute >= 60) {
                            minute = 0;
                        }
                        if (second < 0 || second >= 60) {
                            second = 0;
                        }
                    }
                }
                let month = 1;
                let day = 1;
                let dts = pt.split("-");
                if (dts.length === 1) {
                    let year = parseInt(dts[0]);
                } else if (dts.length === 2) {
                    let year = parseInt(dts[0]);
                    let month = parseInt(dts[1]);
                } else if (dts.length === 3) {
                    let year = parseInt(dts[0]);
                    let month = parseInt(dts[1]);
                    let day = parseInt(dts[2]);
                } else {
                    throw new Error(`Invalid date format: ${pt}`);
                }
                if (month < 1 || month > 12) {
                    month = 1;
                }
                if (day < 1 || day > 31) {
                    day = 1;
                }
                jdt = IndraTime.discreteTimeToJulian(year, month, day, hour, minute, second, microsecond);
            }
            results.push(jdt);
        }
        return results;
    }

}