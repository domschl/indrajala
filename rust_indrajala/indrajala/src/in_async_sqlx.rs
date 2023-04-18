use crate::IndraEvent;
use async_std::task;
use sqlx::sqlite::{SqliteConnectOptions, SqlitePool};
use std::time::Duration;

use crate::indra_config::SQLxConfig;
use crate::{AsyncTaskReceiver, AsyncTaskSender, IndraTask}; // , IndraTask} //, TaskInit};

#[derive(Clone)]
pub struct SQLx {
    pub config: SQLxConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
    pub task: IndraTask,
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
                pool: async_init(&mut config).await,
                task: IndraTask {
                    name: "SQLx".to_string(),
                    active: config.active,
                    out_topics: config.clone().out_topics.clone(),
                    out_channel: s1,
                },
            }
        })
    }
}

async fn async_init(config: &mut SQLxConfig) -> Option<SqlitePool> {
    // Connect to the database
    //let pl: Option<SqlitePool> = None;
    println!("SQLx::init: {:?}", config.database_url.as_str());
    // Configure the connection options
    let fnam = config.database_url.as_str();
    let options = SqliteConnectOptions::new()
        .filename(fnam)
        .create_if_missing(true);
    let mut pool: Option<SqlitePool>;
    let pool_res = sqlx::SqlitePool::connect_with(options).await;
    match pool_res {
        Ok(pool_res) => {
            println!("SQLx::init: Connected to database");
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
                        time_start ISO8601 NOT NULL,
                        data_type TEXT NOT NULL,
                        data JSON NOT NULL,
                        auth_hash TEXT,
                        time_end ISO8601
                    )
                    "#,
    )
    .execute(&pool.clone().unwrap())
    .await;
    match q_res {
        Ok(_) => {
            println!("SQLx::init: Table created");
        }
        Err(e) => {
            println!("SQLx::init: Error creating table: {:?}", e);
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
        println!("IndraTask SQLx::sender");
        let pool = self.pool;
        loop {
            let msg = self.receiver.recv().await.unwrap();
            println!("received route");
            if self.config.active {
                println!("SQLx::sender: {:?}", msg);
                // Insert a new record into the table
                let rows_affected = sqlx::query(
                        r#"
                            INSERT INTO indra_events (domain, from_instance, from_uuid4, to_scope, time_start, data_type, data, auth_hash, time_end)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            "#,
                    )
                    .bind(msg.domain)
                    .bind(msg.from_instance)
                    .bind(msg.from_uuid4)
                    .bind(msg.to_scope)
                    .bind(msg.time_start)
                    .bind(msg.data_type)
                    .bind(msg.data.to_string())
                    .bind(msg.auth_hash)
                    .bind(msg.time_end)
                    .execute(&pool.clone().unwrap())
                    .await.unwrap()
                    .rows_affected();

                println!("Inserted {} row(s)", rows_affected);
            }
        }
    }
}

impl AsyncTaskSender for SQLx {
    async fn async_receiver(self, sender: async_channel::Sender<IndraEvent>) {
        loop {
            let dd: IndraEvent;
            dd = IndraEvent::new();
            //dd.data = serde_json(b);
            //println!("SQLx::sender: {:?}", dd);
            async_std::task::sleep(Duration::from_millis(1000)).await;
            if self.config.active {
                //sender.send(dd).await.unwrap();
            }
        }
    }
}
