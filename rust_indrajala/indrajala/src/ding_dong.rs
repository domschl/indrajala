use crate::IndraEvent;
use std::time::Duration;

use crate::indra_config::DingDongConfig;
use crate::{AsyncTaskReceiver, AsyncTaskSender, IndraTask}; // , IndraTask} //, TaskInit};

#[derive(Clone)]
pub struct DingDong {
    pub config: DingDongConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
    pub task: IndraTask,
}

impl DingDong {
    pub fn new(config: DingDongConfig) -> Self {
        let s1: async_channel::Sender<IndraEvent>;
        let r1: async_channel::Receiver<IndraEvent>;
        (s1, r1) = async_channel::unbounded();
        DingDong {
            config: config.clone(),
            receiver: r1,
            task: IndraTask {
                name: "DingDong".to_string(),
                active: config.active,
                out_topics: config.clone().out_topics.clone(),
                out_channel: s1,
            },
        }
    }
}

impl AsyncTaskReceiver for DingDong {
    async fn async_sender(self) {
        println!("IndraTask DingDong::sender");
        loop {
            let msg = self.receiver.recv().await;
            if self.config.active {
                println!("DingDong::sender: {:?}", msg);
            }
        }
    }
}

impl AsyncTaskSender for DingDong {
    async fn async_receiver(self, sender: async_channel::Sender<IndraEvent>) {
        loop {
            let a = &self.config.topic;
            let b = &self.config.message;
            let mut dd: IndraEvent;
            dd = IndraEvent::new();
            dd.domain = a.to_string();
            dd.data = serde_json::json!(b);
            //dd.data = serde_json(b);
            async_std::task::sleep(Duration::from_millis(self.config.timer)).await;
            if self.config.active {
                sender.send(dd).await.unwrap();
            }
        }
    }
}