use crate::IndraEvent;
use std::time::Duration;

use crate::indra_config::DingDongConfig; //, IndraTaskConfig};
use crate::{AsyncTaskReceiver, AsyncTaskSender}; // , IndraTask} //, TaskInit};

#[derive(Clone)]
pub struct DingDong {
    pub config: DingDongConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
    pub sender: async_channel::Sender<IndraEvent>,
}

impl DingDong {
    pub fn new(config: DingDongConfig) -> Self {
        let s1: async_channel::Sender<IndraEvent>;
        let r1: async_channel::Receiver<IndraEvent>;
        (s1, r1) = async_channel::unbounded();
        DingDong {
            config: config.clone(),
            receiver: r1,
            sender: s1,
        }
    }
}

impl AsyncTaskReceiver for DingDong {
    async fn async_receiver(mut self) {
        // println!("IndraTask DingDong::sender");
        loop {
            let msg = self.receiver.recv().await.unwrap();
            if msg.domain == "$cmd/quit" {
                println!("ding_dong: Received quit command, quiting receive-loop.");
                self.config.active = false;
                break;
            }

            if self.config.active {
                //println!("DingDong::sender: {:?}", msg);
            }
        }
    }
}

impl AsyncTaskSender for DingDong {
    async fn async_sender(self, sender: async_channel::Sender<IndraEvent>) {
        loop {
            let a = &self.config.topic;
            let b = &self.config.message;
            let mut dd: IndraEvent;
            dd = IndraEvent::new();
            dd.domain = a.to_string();
            dd.from_instance = self.config.name.to_string();
            dd.data = serde_json::json!(b);
            //dd.data = serde_json(b);
            async_std::task::sleep(Duration::from_millis(self.config.timer)).await;
            if self.config.active {
                if sender.send(dd).await.is_err() {
                    println!("DingDong: Error sending message to channel, assuming shutdown.");
                    break;
                }
            } else {
                println!("DingDong: quitting send-loop.");
                break;
            }
        }
    }
}
