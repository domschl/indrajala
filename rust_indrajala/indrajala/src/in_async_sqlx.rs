use crate::IndraEvent;
use sqlx::sqlite::SqlitePool;
use std::time::Duration;

use crate::indra_config::SQLxConfig;
use crate::{AsyncTaskReceiver, AsyncTaskSender, IndraTask}; // , IndraTask} //, TaskInit};

#[derive(Clone)]
pub struct SQLx {
    pub config: SQLxConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
    pub task: IndraTask,
}

impl SQLx {
    pub fn new(config: SQLxConfig) -> Self {
        let s1: async_channel::Sender<IndraEvent>;
        let r1: async_channel::Receiver<IndraEvent>;
        (s1, r1) = async_channel::unbounded();

        // Connect to the database
        let pool = SqlitePool::connect(self.config.database_url).await?;

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
        .execute(&pool)
        .await?;

        //Ok(())

        return SQLx {
            config: config.clone(),
            receiver: r1,
            task: IndraTask {
                name: "SQLx".to_string(),
                active: config.active,
                out_topics: config.clone().out_topics.clone(),
                out_channel: s1,
            },
        };
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
            let mut dd: IndraEvent;
            dd = IndraEvent::new();
            //dd.data = serde_json(b);
            async_std::task::sleep(Duration::from_millis(1000)).await;
            if self.config.active {
                sender.send(dd).await.unwrap();
            }
        }
    }
}
