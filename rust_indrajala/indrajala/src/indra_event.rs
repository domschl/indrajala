use chrono::{DateTime, Utc};
use chrono_tz::Tz;
use chrono_tz::UTC;

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

impl IndraTime {
    fn new() -> IndraTime {
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
