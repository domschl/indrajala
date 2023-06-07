use chrono::{DateTime, Datelike, TimeZone, Timelike, Utc};
use serde::{Deserialize, Serialize};
//use serde_json::Result;

/*
struct IndraTime {
    repr: String,
    dt: DateTime<Utc>,
    bp0: i64,
    dt0: i64,
    year_solar_days: f64,
    len_year: f64,
    max_bc_age: i32,
    bc_max: f64,
}
*/
/*
impl IndraTime {
    pub fn new() -> IndraTime {
        let bp0 = Utc.ymd(1950, 1, 1).and_hms(0, 0, 0).timestamp();
        let dt0 = Utc.ymd(1, 1, 1).and_hms(0, 0, 0).timestamp();
        let year_solar_days = 365.24217;
        let len_year = year_solar_days * 24.0 * 3600.0;
        let mut indratime = IndraTime {
            repr: "dt".to_string(),
            dt: Utc::now(),
            bp0,
            dt0,
            year_solar_days,
            len_year,
            max_bc_age: 5000,
            bc_max: dt0 - (5000 as f64 * len_year),
        };
        indratime.set_max_bc_range(5000);
        indratime
    }

    fn year2sec(&self, yr: i32) -> f64 {
        yr as f64 * self.len_year
    }

    fn set_max_bc_range(&mut self, bc_year: i32) {
        self.max_bc_age = bc_year;
        self.bc_max = self.dt0 as f64 - self.year2sec(self.max_bc_age);
    }

    fn set_datetime(&mut self, dt: DateTime<Utc>) {
        self.repr = "dt".to_string();
        self.dt = dt;
    }

    fn set_timestamp(&mut self, t: i64) {
        if t < self.dt0 {
            self.repr = "it".to_string();
            //self.it = t;
        } else {
            self.repr = "dt".to_string();
            self.dt = DateTime::<Utc>::from_utc(NaiveDateTime::from_timestamp(t, 0), Utc);
        }
    }

    fn set_bp(&mut self, bp: i64) -> DateTime<Utc> {
        let ut = self.bp0 - bp;
        if ut >= self.dt0 {
            self.dt = DateTime::<Utc>::from_utc(NaiveDateTime::from_timestamp(ut, 0), Utc);
            self.repr = "dt".to_string();
            return self.dt;
        } else {
            //self.it = ut;
            self.repr = "it".to_string();
            return Utc::now();
        }
    }

    fn set_ybp(&mut self, ybp: i32) -> DateTime<Utc> {
        return self.set_bp((ybp as f64 * self.len_year) as i64);
    }

    fn set_ybc(&mut self, ybc: i32) -> f64 {
        //self.it = (-1 * (ybc - 1) * (self.len_year as i32)) + (self.dt0 as i32);
        return (-1 * (ybc - 1) * (self.len_year as i32)) as f64 + (self.dt0 as f64);
    }
}
*/

pub const INDRA_EVENT_VERSION: i64 = 1;

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct IndraEvent {
    pub domain: String,
    pub from_id: String,
    pub uuid4: String,
    pub to_scope: String,
    pub time_jd_start: f64,
    pub data_type: String,
    pub data: String,
    pub auth_hash: Option<String>,
    pub time_jd_end: Option<f64>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub enum IndraHistoryRequestMode {
    Interval,
    Single,
    Sample,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct IndraHistoryRequest {
    pub domain: String,
    pub mode: IndraHistoryRequestMode,
    pub data_type: String,
    pub time_jd_start: Option<f64>,
    pub time_jd_end: Option<f64>,
    pub limit: Option<u32>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct IndraUniqueDomainsRequest {
    pub domain: Option<String>,
    pub data_type: Option<String>,
}

impl IndraEvent {
    pub fn new(// domain: String,
       // from_instance: String,
        //from_uuid4: String,
        //to_scope: String,
        //time_start: String,
        //data_type: String,
        //data: serde_json::Value,
        //auth_hash: Option<String>,
        //time_end: Option<String>,
    ) -> IndraEvent {
        let now: DateTime<Utc> = Utc::now();
        //Utc::now();
        // let iso_string = now.to_rfc3339_opts(chrono::SecondsFormat::Millis, true);
        //let iso_string = now.to_rfc3339_opts(chrono::SecondsFormat::Secs, true);
        // println!("{}", iso_string);
        IndraEvent {
            domain: "".to_string(), // The recipient domain, PUBLISHER topic which can be subscribed to
            from_id: "".to_string(), // The sender instance domain , a reverse PUBLISHER topic which can be used to reply, if used in transaction mode
            uuid4: "".to_string(),   // A uuid for the event, used to prevent duplicate events
            to_scope: "".to_string(), // A session scope, used to group events into sessions and to allow authentication hierachies. Domain-like syntax.
            time_jd_start: Self::datetime_to_julian(now), // The start time of the event, in Julian Date
            data_type: "".to_string(), // The type of the data, used to allow filtering, domain-like syntax, e.g. "number/float"
            data: "".to_string(),      // The data, can be any JSON value, described by data_type
            auth_hash: Default::default(), // A hash of the data, used to authenticate the data
            time_jd_end: Default::default(), // The end time of the event, in Julian Date
        }
    }

    //pub fn to_json(&self) -> Result<String> {
    //    serde_json::to_string(self)
    //}

    //pub fn from_json(text: &String) -> Result<IndraEvent> {
    //    serde_json::from_str(text.as_str())
    //}

    pub fn datetime_to_julian(dt: DateTime<Utc>) -> f64 {
        // XXX unchecked copilot mess
        let year = dt.year();
        let month = dt.month() as i32;
        let day = dt.day() as i32;

        let a = (14 - month) / 12;
        let y = year + 4800 - a;
        let m = month + 12 * a - 3;

        let julian_day_number =
            day + (153 * m + 2) / 5 + 365 * y + y / 4 - y / 100 + y / 400 - 32045;
        //let julian_date =
        // Julian Date:
        julian_day_number as f64
            + (dt.hour() as f64 - 12.0) / 24.0
            + dt.minute() as f64 / 1440.0
            + dt.second() as f64 / 86400.0
            + dt.timestamp_subsec_micros() as f64 / 86400000000.0
    }

    pub fn julian_to_datetime(jd: f64) -> DateTime<Utc> {
        // XXX unchecked copilot mess
        let jd = jd + 0.5;
        let z = jd as i64;
        let f = jd - z as f64;
        let mut a = z;
        if z >= 2299161 {
            let alpha = ((z as f64 - 1867216.25) / 36524.25).floor() as i64;
            a = z + 1 + alpha - (alpha / 4);
        }
        let b = a + 1524;
        let c = ((b as f64 - 122.1) / 365.25).floor() as i64;
        let d = (365.25 * c as f64).floor() as i64;
        let e = ((b - d) as f64 / 30.6001).floor() as i64;
        let day = b - d - (30.6001 * e as f64).floor() as i64;
        let month = if e < 14 { e - 1 } else { e - 13 };
        let year = if month > 2 { c - 4716 } else { c - 4715 };
        let hour = (f * 24.0).floor() as u32;
        let minute = ((f * 24.0 - hour as f64) * 60.0).floor() as u32;
        let second = (((f * 24.0 - hour as f64) * 60.0 - minute as f64) * 60.0).floor() as u32;
        let microsecond =
            (((((f * 24.0 - hour as f64) * 60.0 - minute as f64) * 60.0 - second as f64) * 1000.0)
                * 1000.0)
                .floor() as u32;
        chrono::Utc
            .with_ymd_and_hms(year as i32, month as u32, day as u32, hour, minute, second)
            .unwrap()
            .with_nanosecond(microsecond * 1_000)
            .unwrap()
    }

    pub fn mqcmp(pub_str: &str, sub: &str) -> bool {
        for c in ["+", "#"] {
            if pub_str.contains(c) {
                println!("Illegal char '{}' in pub in mqcmp!", c);
                return false;
            }
        }
        let mut inds = 0;
        let mut wcs = false;
        for (_indp, c) in pub_str.chars().enumerate() {
            if wcs {
                if c == '/' {
                    inds += 1;
                    wcs = false;
                }
                continue;
            }
            if inds >= sub.len() {
                return false;
            }
            if c == sub.chars().nth(inds).unwrap() {
                inds += 1;
                continue;
            }
            if sub.chars().nth(inds).unwrap() == '#' {
                return true;
            }
            if sub.chars().nth(inds).unwrap() == '+' {
                wcs = true;
                inds += 1;
                continue;
            }
            if c != sub.chars().nth(inds).unwrap() {
                return false;
            }
        }
        if sub[inds..].is_empty() {
            return true;
        }
        //if sub[inds..].len() == 1 {
        //    if sub.chars().nth(inds).unwrap() == '+' || sub.chars().nth(inds).unwrap() == '#' {
        //        return true;
        //    }
        //}
        if sub[inds..].len() == 1
            && (sub.chars().nth(inds).unwrap() == '+' || sub.chars().nth(inds).unwrap() == '#')
        {
            return true;
        }

        false
    }

    pub fn check_route(
        ie_domain: &str,
        _name: &str,
        subs: &Vec<String>,
        blocks: Option<&Vec<String>>,
    ) -> bool {
        for topic in subs {
            if IndraEvent::mqcmp(ie_domain, topic) {
                let mut blocked = false;
                if let Some(blocks) = blocks {
                    for out_block in blocks {
                        if IndraEvent::mqcmp(ie_domain, out_block) {
                            // println!("router: {} {} {} blocked", name, topic, ie_domain);
                            blocked = true;
                        }
                    }
                }
                //if blocks.is_some() {
                //    for out_block in blocks.unwrap() {
                //        if IndraEvent::mqcmp(ie_domain, out_block) {
                //            // println!("router: {} {} {} blocked", name, topic, ie_domain);
                //            blocked = true;
                //        }
                //    }
                //}

                if blocked {
                    continue;
                }
                return true;
            }
        }
        false
    }

    pub fn _reverse_path(path: &str) -> String {
        let mut elements: Vec<&str> = path.split('/').collect();
        elements.reverse();
        elements.join("/")
    }
}

impl Default for IndraEvent {
    fn default() -> Self {
        Self::new()
    }
}

/*
pub fn add(left: usize, right: usize) -> usize {
    left + right
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn it_works() {
        let result = add(2, 2);
        assert_eq!(result, 4);
    }
}
*/
