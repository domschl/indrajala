use crate::IndraEvent;
use async_std::task;
//use chrono::format;
use sqlx::sqlite::{SqliteConnectOptions, SqlitePool};
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
    pub pool: Option<SqlitePool>,
}

//pub const INDRA_EVENT_DB_VERSION: i64 = 1;

impl SQLx {
    pub fn new(mut config: SQLxConfig) -> Self {
        let s1: async_channel::Sender<IndraEvent>;
        let r1: async_channel::Receiver<IndraEvent>;
        (s1, r1) = async_channel::unbounded();

        task::block_on(async {
            let pool= async_init(&mut config).await;
            SQLx {
                config: config.clone(),
                receiver: r1,
                sender: s1,
                pool: pool,
            }
        })
    }
}

async fn async_init(config: &mut SQLxConfig) -> Option<SqlitePool> {
    let fnam = config.database_url.clone();
    let db_sync: &str;


    match config.db_sync {
        DbSync::Sync => {
            db_sync = "NORMAL";
        }
        DbSync::Async => {
            db_sync = "OFF";
        }
    }
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
            error!("SQLx::init: Error connecting to database {}: {:?}", fnam.clone(), e);
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
                        from_instance TEXT NOT NULL,
                        from_uuid4 UUID NOT NULL,
                        to_scope TEXT NOT NULL,
                        time_jd_start DOUBLE,
                        data_type TEXT NOT NULL,
                        data JSON NOT NULL,
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
    return pool;
}

impl AsyncTaskReceiver for SQLx {
    async fn async_receiver(mut self) {
        if self.config.active == false {
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
            }
            if msg.domain.starts_with("$cmd/") {
                if msg.domain.starts_with("$cmd/db/req/") {
                    let remainder = &msg.domain[12..];
                    debug!(
                        "SQLx: Received db/req command from {} search for: {}",
                        msg.from_instance, remainder
                    );
                    let pool = pool.clone().unwrap();
                    let rows: Vec<(i64, f64, String)> = sqlx::query_as(
                        "SELECT id, time_jd_start, data FROM indra_events WHERE domain = ?",
                    )
                    .bind(remainder.to_string())
                    .fetch_all(&pool)
                    .await
                    .unwrap();
                    debug!("Found {} items", rows.len());
                    let res: Vec<(f64, f64)> = rows
                        .iter()
                        .map(|row| {
                            let data: serde_json::Value = serde_json::from_str(&row.2).unwrap();
                            let num_text: String = data.to_string().replace("\"", "");
                            let data_f64: f64 = num_text.trim().parse().unwrap();
                            let time_jd_start: f64 = row.1;
                            // let time_jd_end: f64 = serde_json::from_value(data["time_jd_end"].clone()).unwrap();
                            (time_jd_start, data_f64)
                        })
                        .collect();
                    debug!("Found {} items: {:?}", res.len(), res);
                    for row in res {
                        debug!("Found item: {:?}", row);
                    }
                    continue;
                }
                warn!("SQLx: Received unknown command: {:?}", msg.domain);
                continue;
            }

            if self.config.active {
                debug!("SQLx::sender: {:?}", msg);
                // Insert a new record into the table
                let rows_affected = sqlx::query(
                        r#"
                            INSERT INTO indra_events (domain, from_instance, from_uuid4, to_scope, time_jd_start, data_type, data, auth_hash, time_jd_end)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            "#,
                    )
                    .bind(msg.domain)
                    .bind(msg.from_instance)
                    .bind(msg.from_uuid4)
                    .bind(msg.to_scope)
                    .bind(msg.time_jd_start)
                    .bind(msg.data_type)
                    .bind(msg.data.to_string())
                    .bind(msg.auth_hash)
                    .bind(msg.time_jd_end)
                    .execute(&pool.clone().unwrap())
                    .await.unwrap()
                    .rows_affected();

                debug!("Inserted {} row(s)", rows_affected);
            }
        }
    }
}

impl AsyncTaskSender for SQLx {
    async fn async_sender(self, _sender: async_channel::Sender<IndraEvent>) {
        loop {
            let _dd: IndraEvent;
            _dd = IndraEvent::new();
            async_std::task::sleep(Duration::from_millis(1000)).await;
            if self.config.active {
                //sender.send(dd).await.unwrap();
            }
        }
    }
}
