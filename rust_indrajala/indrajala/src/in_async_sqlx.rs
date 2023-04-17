use crate::IndraEvent;
use sqlx::sqlite::{SqliteConnectOptions, SqlitePool};
use std::str::FromStr;
use std::time::Duration;

use crate::indra_config::SQLxConfig;
use crate::{AsyncTaskInit, AsyncTaskReceiver, AsyncTaskSender, IndraTask}; // , IndraTask} //, TaskInit};

#[derive(Clone)]
pub struct SQLx {
    pub config: SQLxConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
    pub task: IndraTask,
    pub pool: Option<SqlitePool>,
}

impl SQLx {
    pub fn new(config: SQLxConfig) -> Self {
        let s1: async_channel::Sender<IndraEvent>;
        let r1: async_channel::Receiver<IndraEvent>;
        (s1, r1) = async_channel::unbounded();

        SQLx {
            config: config.clone(),
            receiver: r1,
            pool: None,
            task: IndraTask {
                name: "SQLx".to_string(),
                active: config.active,
                out_topics: config.clone().out_topics.clone(),
                out_channel: s1,
            },
        }
    }
}

impl AsyncTaskInit for SQLx {
    async fn async_init(mut self) -> bool {
        // Connect to the database
        //let pl: Option<SqlitePool> = None;
        println!("SQLx::init: {:?}", self.config.database_url.as_str());
        // Configure the connection options
        let fnam = self.config.database_url.as_str();
        let options = SqliteConnectOptions::new()
            .filename(fnam)
            .create_if_missing(true);
        self.pool = Some(sqlx::SqlitePool::connect_with(options).await.unwrap());

        // Create a new table
        sqlx::query(
            r#"
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        age INTEGER NOT NULL
                    )
                    "#,
        )
        .execute(&self.pool.unwrap())
        .await
        .unwrap();
        return true;
    }
}

impl AsyncTaskReceiver for SQLx {
    async fn async_sender(self) {
        println!("IndraTask SQLx::sender");
        loop {
            let msg = self.receiver.recv().await;
            if self.config.active {
                println!("SQLx::sender: {:?}", msg);
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
            async_std::task::sleep(Duration::from_millis(1000)).await;
            if self.config.active {
                sender.send(dd).await.unwrap();
            }
        }
    }
}
