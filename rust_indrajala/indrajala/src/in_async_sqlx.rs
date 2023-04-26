use crate::IndraEvent;
use async_std::task;
use sqlx::sqlite::{SqliteConnectOptions, SqlitePool};
use std::time::Duration;

use crate::indra_config::SQLxConfig;
use crate::{AsyncTaskReceiver, AsyncTaskSender};

#[derive(Clone)]
pub struct SQLx {
    pub config: SQLxConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
    pub sender: async_channel::Sender<IndraEvent>,
    pub pool: Option<SqlitePool>,
}

impl SQLx {
    pub fn new(mut config: SQLxConfig) -> Self {
        let s1: async_channel::Sender<IndraEvent>;
        let r1: async_channel::Receiver<IndraEvent>;
        (s1, r1) = async_channel::unbounded();

        task::block_on(async {
            SQLx {
                config: config.clone(),
                receiver: r1,
                sender: s1,
                pool: async_init(&mut config).await,
            }
        })
    }
}

async fn async_init(config: &mut SQLxConfig) -> Option<SqlitePool> {
    //println!("SQLx::init: {:?}", config.database_url.as_str());
    let fnam = config.database_url.as_str();
    let options = SqliteConnectOptions::new()
        .filename(fnam)
        .create_if_missing(true);
    let mut pool: Option<SqlitePool>;
    let pool_res = sqlx::SqlitePool::connect_with(options).await;
    match pool_res {
        Ok(pool_res) => {
            //println!("SQLx::init: Connected to database");
            pool = Some(pool_res);
        }
        Err(e) => {
            println!("SQLx::init: Error connecting to database: {:?}", e);
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
            // println!("SQLx::init: Table created");
        }
        Err(e) => {
            println!("SQLx::init: Error creating table: {:?}", e);
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
            //println!("SQLx::init: Indices created");
        }
        Err(e) => {
            println!("SQLx::init: Error creating indices: {:?}", e);
            config.active = false;
            pool = None;
        }
    }
    return pool;
}

impl AsyncTaskReceiver for SQLx {
    async fn async_sender(self) {
        if self.config.active == false {
            return;
        }
        //println!("IndraTask SQLx::sender");
        let pool = self.pool;
        loop {
            let msg = self.receiver.recv().await.unwrap();
            //println!("received route");
            if self.config.active {
                //println!("SQLx::sender: {:?}", msg);
                // Insert a new record into the table
                let _rows_affected = sqlx::query(
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

                //println!("Inserted {} row(s)", rows_affected);
            }
        }
    }
}

impl AsyncTaskSender for SQLx {
    async fn async_receiver(self, _sender: async_channel::Sender<IndraEvent>) {
        loop {
            let _dd: IndraEvent;
            _dd = IndraEvent::new();
            //dd.data = serde_json(b);
            //println!("SQLx::sender: {:?}", dd);
            async_std::task::sleep(Duration::from_millis(1000)).await;
            if self.config.active {
                //sender.send(dd).await.unwrap();
            }
        }
    }
}

//use sqlx::sqlite::SqlitePool;
// use std::env;

// Wildcard query on domain:

//#[async_std::main]
async fn _main_searcher() -> Result<(), sqlx::Error> {
    let db_url = "sqlite://test.db";
    let pool = SqlitePool::connect(db_url).await?;

    // Create table and index
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_items_name ON items(name);
        "#,
    )
    .execute(&pool)
    .await?;

    // Insert some data
    sqlx::query("INSERT INTO items (name) VALUES ('apple'), ('banana'), ('cherry')")
        .execute(&pool)
        .await?;

    // Query using index
    let prefix = "ba";
    let rows: Vec<(i64, String)> =
        sqlx::query_as("SELECT id, name FROM items WHERE name >= ? AND name < ? ORDER BY name")
            .bind(prefix)
            .bind(format!("{}{}", prefix, '\u{ffff}'))
            .fetch_all(&pool)
            .await?;

    for row in rows {
        println!("id: {}, name: {}", row.0, row.1);
    }

    Ok(())
}
