use crate::IndraEvent;
use std::time::Duration;

//use env_logger::Env;
//use log::{debug, error, info, warn};
use log::{debug, warn};

use crate::indra_config::DingDongConfig; //, IndraTaskConfig};
                                         //use crate::{AsyncTaskReceiver, AsyncTaskSender}; // , IndraTask} //, TaskInit};
use crate::AsyncIndraTask;

#[derive(Clone)]
pub struct DingDong {
    pub config: DingDongConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
    pub sender: async_channel::Sender<IndraEvent>,
    pub subs: Vec<String>,
}

impl DingDong {
    pub fn new(config: DingDongConfig) -> Self {
        let s1: async_channel::Sender<IndraEvent>;
        let r1: async_channel::Receiver<IndraEvent>;
        (s1, r1) = async_channel::unbounded();
        let subs = vec![format!("{}/#", config.name)];

        DingDong {
            config,
            receiver: r1,
            sender: s1,
            subs,
        }
    }
}

impl AsyncIndraTask for DingDong {
    async fn async_receiver(mut self, _sender: async_channel::Sender<IndraEvent>) {
        if !self.config.active {
            return;
        }
        loop {
            let msg = self.receiver.recv().await.unwrap();
            if msg.domain == "$cmd/quit" {
                debug!("ding_dong: Received quit command, quiting receive-loop.");
                self.config.active = false;
                break;
            }

            if self.config.active {
                debug!("DingDong::receiver: {:?}", msg);
            }
        }
    }

    async fn async_sender(self, sender: async_channel::Sender<IndraEvent>) {
        if !self.config.active {
            return;
        }
        loop {
            let a = &self.config.topic;
            let b = &self.config.message;
            let mut dd: IndraEvent;
            dd = IndraEvent::new();
            dd.domain = a.to_string();
            dd.from_id = self.config.name.to_string();
            dd.data = b.to_string();
            //dd.data = serde_json(b);
            async_std::task::sleep(Duration::from_millis(self.config.timer)).await;
            if self.config.active {
                if sender.send(dd).await.is_err() {
                    warn!("DingDong: Error sending message to channel, assuming shutdown.");
                    break;
                }
            } else {
                debug!("DingDong: quitting send-loop.");
                break;
            }
        }
    }
}