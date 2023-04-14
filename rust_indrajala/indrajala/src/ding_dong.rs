use crate::indra_config::IndraConfig;
use crate::IndraEvent;
use std::future::Future;
use std::time::Duration;

use crate::{AsyncTaskInit, AsyncTaskReceiver, AsyncTaskSender, IndraTask, TaskInit};

#[derive(Clone)]
pub struct DingDong {
    pub topic: String,
    pub message: String,
    pub timer: u64,
}

impl TaskInit for DingDong {
    fn init(mut self, indra_config: IndraConfig, indra_task: IndraTask) -> u32 {
        println!("IndraTask::init");
        self.topic = indra_config.dingdong.topic;
        self.message = indra_config.dingdong.message;
        self.timer = indra_config.dingdong.timer;
        return 0;
    }
}

impl AsyncTaskInit for DingDong {
    async fn async_init(self, indra_config: IndraConfig, indra_task: IndraTask) -> u32 {
        println!("DingDong::async_init");
        //self.topic = indra_config.dingdong.topic;
        //self.message = indra_config.dingdong.message;
        //self.timer = indra_config.dingdong.timer;
        return 0;
    }
}

impl AsyncTaskReceiver for DingDong {
    async fn async_sender(self, indra_event: &IndraEvent) {
        println!("IndraTask DingDong::sender: {}", indra_event.data);
    }
}

impl AsyncTaskSender for DingDong {
    async fn async_receiver(self, sender: async_channel::Sender<IndraEvent>) {
        //let dingdong_config = &indra_config.dingdong;
        loop {
            let a = &self.topic;
            let b = &self.message;
            let mut dd: IndraEvent;
            dd = IndraEvent::new();
            dd.domain = a.to_string();
            dd.data = serde_json::json!(b);
            //dd.data = serde_json(b);
            async_std::task::sleep(Duration::from_millis(self.timer)).await;
            sender.send(dd).await.unwrap();
        }
    }
}
