use async_std::task;
use chrono::Utc;
use indra_event::{IndraEvent, IndraEventRequest};
use sqlx::sqlite::{SqliteConnectOptions, SqlitePool};
use sqlx::Row;
use std::time::Duration;
//use std::path::Path;

//use env_logger::Env;
//use log::{debug, error, info, warn};
use log::{debug, error, info, warn};

use crate::indra_config::{DbSync, SQLxConfig};
use crate::{AsyncTaskReceiver, AsyncTaskSender};

#[derive(Clone)]
pub struct SQLx {
    pub config: SQLxConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
    pub sender: async_channel::Sender<IndraEvent>,
    pub subs: Vec<String>,
    pub pool: Option<SqlitePool>,
    pub r_sender: Option<async_channel::Sender<IndraEvent>>,
}

//pub const INDRA_EVENT_DB_VERSION: i64 = 1;

impl SQLx {
    pub fn new(mut config: SQLxConfig) -> Self {
        let s1: async_channel::Sender<IndraEvent>;
        let r1: async_channel::Receiver<IndraEvent>;
        (s1, r1) = async_channel::unbounded();
        //let sq_config = config.clone();
        let def_addr = "$trx/db/#".to_string();
        let subs = vec![
            "$event/#".to_string(),
            def_addr,
            format!("{}/#", config.name),
        ];

        task::block_on(async {
            let pool = async_init(&mut config).await;
            SQLx {
                config: config.clone(),
                receiver: r1,
                sender: s1,
                subs,
                pool,
                r_sender: Default::default(),
            }
        })
    }
}

async fn async_init(config: &mut SQLxConfig) -> Option<SqlitePool> {
    let fnam = config.database_url.clone();
    let db_sync: &str = match config.db_sync {
        DbSync::Sync => "NORMAL",
        DbSync::Async => "OFF",
    };
    let options = SqliteConnectOptions::new()
        .filename(fnam.clone())
        .create_if_missing(true)
        .pragma("journal_mode", "WAL") // alternative: DELETE, TRUNCATE, PERSIST, MEMORY, OFF
        //  This line sets the page size of the memory to 4096 bytes. This is the size of a single page in the memory.
        // You can change this if you want to, but please be aware that the page size must be a power of 2.
        // For example, 1024, 2048, 4096, 8192, 16384, etc.
        .pragma("page_size", "4096")
        //  This is the number of pages that will be cached in memory. If you have a lot of memory, you can increase
        // this number to improve performance. If you have a small amount of memory, you can decrease this number to free up memory.
        .pragma("cache_size", "10000")
        // This means that the database will be synced to disk after each transaction. If you don't want this, you can set it to off.
        // However, please be aware that this will make your database more vulnerable to corruption.
        .pragma("synchronous", db_sync) // alternative: OFF, NORMAL, FULL, EXTRA
        .pragma("temp_store", "memory") // alternative: FILE
        .pragma("mmap_size", "1073741824"); // 1Galternative: any positive integer
    let mut pool: Option<SqlitePool>;
    let pool_res = sqlx::SqlitePool::connect_with(options).await;
    match pool_res {
        Ok(pool_res) => {
            info!("SQLx::init: Connected to database {}", fnam.clone());
            pool = Some(pool_res);
        }
        Err(e) => {
            error!(
                "SQLx::init: Error connecting to database {}: {:?}",
                fnam.clone(),
                e
            );
            config.active = false;
            pool = None;
            return pool;
        }
    }
    // let pool = self.pool.clone().unwrap();

    // Create a new table
    let q_res = sqlx::query(
        r#"
                    CREATE TABLE IF NOT EXISTS indra_events (
                        id INTEGER PRIMARY KEY,
                        domain TEXT NOT NULL,
                        from_id TEXT NOT NULL,
                        uuid4 UUID NOT NULL,
                        to_scope TEXT NOT NULL,
                        time_jd_start DOUBLE,
                        data_type TEXT NOT NULL,
                        data TEXT NOT NULL,
                        auth_hash TEXT,
                        time_jd_end DOUBLE
                    )
                    "#,
    )
    .execute(&pool.clone().unwrap())
    .await;
    match q_res {
        Ok(_) => {
            debug!("SQLx::init: Table created");
        }
        Err(e) => {
            error!("SQLx::init: Error creating table: {:?}", e);
            config.active = false;
            pool = None;
        }
    }

    let q_res2 = sqlx::query(
        r#"
                    CREATE INDEX IF NOT EXISTS indra_events_domain ON indra_events (domain);
                    CREATE INDEX IF NOT EXISTS indra_events_from_id ON indra_events (to_scope);
                    CREATE INDEX IF NOT EXISTS indra_events_time_start ON indra_events (time_jd_start);
                    CREATE INDEX IF NOT EXISTS indra_events_data_type ON indra_events (data_type);
                    CREATE INDEX IF NOT EXISTS indra_events_time_end ON indra_events (time_jd_end);
                    "#,
    )
    .execute(&pool.clone().unwrap())
    .await;
    match q_res2 {
        Ok(_) => {
            debug!("SQLx::init: Indices created");
        }
        Err(e) => {
            error!("SQLx::init: Error creating indices: {:?}", e);
            config.active = false;
            pool = None;
        }
    }
    pool
}

impl AsyncTaskReceiver for SQLx {
    async fn async_receiver(mut self, sender: async_channel::Sender<IndraEvent>) {
        if !self.config.active {
            return;
        }
        debug!("IndraTask SQLx::sender");
        let pool = self.pool;
        loop {
            let msg = self.receiver.recv().await.unwrap();
            if msg.domain == "$cmd/quit" {
                debug!("SQLx: Received quit command, quiting receive-loop.");
                if self.config.active {
                    let _ret = &pool.unwrap().close().await;
                    info!("SQLx: Database connection closed.");
                    self.config.active = false;
                }
                break;
            } else if msg.domain.starts_with("$trx/db/") {
                // Random-sampling: SELECT * FROM (SELECT * FROM mytable ORDER BY RANDOM() LIMIT 1000) ORDER BY time;
                if msg.domain.starts_with("$trx/db/req/event/history") {
                    let req: IndraEventRequest = serde_json::from_str(msg.data.as_str()).unwrap();
                    info!(
                        "SQLx: Received db/req/event command from {} search for: {:?}",
                        msg.from_id, req
                    );
                    let rows: Vec<(i64, f64, String)>;
                    let pool = pool.clone().unwrap();
                    if req.time_jd_start.is_none() && req.time_jd_end.is_none() {
                        let rows_res = sqlx::query_as(
                            "SELECT id, time_jd_start, data FROM indra_events WHERE domain = ?",
                        )
                        .bind(req.domain.to_string())
                        .fetch_all(&pool)
                        .await;
                        if rows_res.is_err() {
                            error!(
                                "SQLx: Error executing query on {}, {:?}: {:?}",
                                msg.domain,
                                req,
                                rows_res.err().unwrap()
                            );
                            continue;
                        } else {
                            rows = rows_res.unwrap();
                        }
                    } else if req.time_jd_start.is_some() && req.time_jd_end.is_none() {
                        rows = sqlx::query_as(
                            "SELECT id, time_jd_start, data FROM indra_events WHERE domain = ? AND time_jd_start >= ?",
                        )
                        .bind(req.domain.to_string())
                        .bind(req.time_jd_start.unwrap())
                        .fetch_all(&pool)
                        .await
                        .unwrap();
                    } else if req.time_jd_start.is_none() && req.time_jd_end.is_some() {
                        rows = sqlx::query_as(
                            "SELECT id, time_jd_start, data FROM indra_events WHERE domain = ? AND time_jd_start <= ?",
                        )
                        .bind(req.domain.to_string())
                        .bind(req.time_jd_end.unwrap())
                        .fetch_all(&pool)
                        .await
                        .unwrap();
                    } else if req.time_jd_start.is_some() && req.time_jd_end.is_some() {
                        rows = sqlx::query_as(
                            "SELECT id, time_jd_start, data FROM indra_events WHERE domain = ? AND time_jd_start >= ? AND time_jd_start <= ?",
                        )
                        .bind(req.domain.to_string())
                        .bind(req.time_jd_start.unwrap())
                        .bind(req.time_jd_end.unwrap())
                        .fetch_all(&pool)
                        .await
                        .unwrap();
                    } else {
                        error!(
                            "SQLx: Received invalid db/req command from {} search for: {:?}",
                            msg.from_id, req
                        );
                        continue;
                    }
                    debug!("Found {} items", rows.len());
                    let step: usize;
                    if req.max_count.is_none() {
                        step = 1;
                    } else if rows.len() > req.max_count.unwrap() {
                        step = rows.len() / req.max_count.unwrap();
                    } else {
                        step = 1;
                    }

                    let res: Vec<(f64, f64)> = rows
                        .iter()
                        .step_by(step)
                        .map(|row| {
                            //let data: serde_json::Value = serde_json::from_str(&row.2).unwrap();
                            //let num_text: String = data.to_string().replace("\"", "");
                            //let data_f64_opt = num_text.trim().parse();
                            //let data_f64: f64;
                            //if data_f64_opt.is_err() {
                            //    data_f64 = 0.0;
                            //} else {
                            //    data_f64 = data_f64_opt.unwrap();
                            //}
                            let time_jd_start: f64 = row.1;
                            let data_f64_res = row.2.parse::<f64>();
                            if data_f64_res.is_ok() {
                                #[allow(clippy::unnecessary_unwrap)]
                                let data_f64: f64 = data_f64_res.unwrap();
                                (time_jd_start, data_f64)
                            } else {
                                // insert NaN for invalid data:
                                warn!("SQLx: Invalid f64 value data in row: {:?}", row);
                                let data_f64: f64 = std::f64::NAN;
                                (time_jd_start, data_f64)
                            }
                        })
                        .filter(|row| !row.1.is_nan())
                        .collect();
                    info!(
                        "Found {} items out of raw {} for {}",
                        res.len(),
                        rows.len(),
                        msg.domain
                    );
                    for _row in res.clone() {
                        // debug!("Found item: {:?}", row);
                    }
                    let ut_now = Utc::now();
                    let rmsg = IndraEvent {
                        domain: msg.from_id.clone(), // .replace("$trx/db/req", "$trx/db/reply"),
                        from_id: self.config.name.clone(),
                        uuid4: msg.uuid4.clone(),
                        to_scope: req.domain.clone(),
                        time_jd_start: IndraEvent::datetime_to_julian(ut_now),
                        data_type: "vector/tuple/jd/float".to_string(),
                        data: serde_json::to_string(&res).unwrap(),
                        auth_hash: Default::default(),
                        time_jd_end: Default::default(),
                    };
                    //if self.r_sender.clone().is_none() {
                    //    error!("SQLx: Error sending reply-message to channel {}, r_sender NOT AVAILABLE", rmsg.domain);
                    //    //break;
                    //} else {
                    debug!("Sending: {}->{}", rmsg.from_id, rmsg.domain);
                    if sender.send(rmsg.clone()).await.is_err() {
                        error!(
                            "SQLx: Error sending reply-message to channel {}",
                            rmsg.domain
                        );
                        //break;
                    }
                    //}
                    continue;
                } else if msg.domain.starts_with("$trx/db/req/event/uniquedomains") {
                    debug!("SQLx: Received db/unq/req command from {}", msg.from_id);
                    //let rows: Vec<(String)>;
                    let pool = pool.clone().unwrap();
                    let rows: Vec<String> =
                        sqlx::query("SELECT DISTINCT domain FROM indra_events WHERE data_type LIKE 'number/float%';")
                            .fetch_all(&pool)
                            .await
                            .unwrap()
                            .iter()
                            .map(|rowi| rowi.try_get(0).unwrap())
                            .collect();
                    let ut_now = Utc::now();
                    let rmsg = IndraEvent {
                        domain: msg.from_id.clone().replace("$trx/db/req", "$/trx/db/reply"),
                        from_id: self.config.name.clone(),
                        uuid4: msg.uuid4.clone(),
                        to_scope: "".to_string(),
                        time_jd_start: IndraEvent::datetime_to_julian(ut_now),
                        data_type: "vector/string/uniquedomains".to_string(),
                        data: serde_json::to_string(&rows).unwrap(),
                        auth_hash: Default::default(),
                        time_jd_end: Default::default(),
                    };
                    warn!("Sending domain-list: {}->{}", rmsg.from_id, rmsg.domain);
                    if sender.send(rmsg.clone()).await.is_err() {
                        error!(
                            "SQLx: Error sending reply-message to channel {}",
                            rmsg.domain
                        );
                    }
                    continue;
                }
                warn!("SQLx: Received unknown command: {:?}", msg.domain);
                continue;
            } else if msg.domain.starts_with("$event/") {
                let domain = msg.domain.clone();
                let data_str = msg.data.clone();
                if self.config.active {
                    // ignore Ws* domains
                    debug!("SQLx::sender: {:?}", msg);
                    // Insert a new record into the table
                    // XXX, check if data_type and data match!
                    let rows_affected = sqlx::query(
                            r#"
                                INSERT INTO indra_events (domain, from_id, uuid4, to_scope, time_jd_start, data_type, data, auth_hash, time_jd_end)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                "#,
                        )
                        .bind(domain)
                        .bind(msg.from_id)
                        .bind(msg.uuid4)
                        .bind(msg.to_scope)
                        .bind(msg.time_jd_start)
                        .bind(msg.data_type)
                        .bind(data_str)
                        .bind(msg.auth_hash)
                        .bind(msg.time_jd_end)
                        .execute(&pool.clone().unwrap())
                        .await.unwrap()
                        .rows_affected();

                    debug!("Inserted {} row(s)", rows_affected);
                }
            } else {
                warn!("SQLx::sender: Received unknown domain: {:?}", msg.domain);
            }
        }
    }
}

impl AsyncTaskSender for SQLx {
    async fn async_sender(self, _sender: async_channel::Sender<IndraEvent>) {
        loop {
            let _dd: IndraEvent = IndraEvent::new();
            async_std::task::sleep(Duration::from_millis(1000)).await;
            if self.config.active {
                //sender.send(dd).await.unwrap();
            }
        }
    }
}
