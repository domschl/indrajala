//use crate::indra_config::IndraConfig;
use crate::IndraEvent;
//use std::future::Future;
use std::time::Duration;

use crate::indra_config::DingDongConfig;
use crate::{AsyncTaskReceiver, AsyncTaskSender}; // , IndraTask} //, TaskInit};

#[derive(Clone)]
pub struct DingDong {
    pub config: DingDongConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
}

/*
impl TaskInit for DingDong {
    fn init(mut self, indra_config: IndraConfig, indra_task: IndraTask) -> bool {
        println!("IndraTask::init");
        self.topic = indra_config.dingdong.topic;
        self.message = indra_config.dingdong.message;
        self.timer = indra_config.dingdong.timer;
        return true;
    }
}

impl AsyncTaskInit for DingDong {
    async fn async_init(self, indra_config: IndraConfig, indra_task: IndraTask) -> bool {
        println!("DingDong::async_init");
        //self.topic = indra_config.dingdong.topic;
        //self.message = indra_config.dingdong.message;
        //self.timer = indra_config.dingdong.timer;
        return true;
    }
}
*/

impl AsyncTaskReceiver for DingDong {
    async fn async_sender(self) {
        println!("IndraTask DingDong::sender");
        loop {
            let msg = self.receiver.recv().await;
            println!("DingDong::sender: {:?}", msg);
        }
    }
}

impl AsyncTaskSender for DingDong {
    async fn async_receiver(self, sender: async_channel::Sender<IndraEvent>) {
        //let dingdong_config = &indra_config.dingdong;
        loop {
            let a = &self.config.topic;
            let b = &self.config.message;
            let mut dd: IndraEvent;
            dd = IndraEvent::new();
            dd.domain = a.to_string();
            dd.data = serde_json::json!(b);
            //dd.data = serde_json(b);
            async_std::task::sleep(Duration::from_millis(self.config.timer)).await;
            sender.send(dd).await.unwrap();
        }
    }
}
