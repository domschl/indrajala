use crate::indra_config::WsConfig;
use crate::IndraEvent;
use crate::{AsyncTaskReceiver, AsyncTaskSender};

#[derive(Clone)]
pub struct Ws {
    pub config: WsConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
    pub sender: async_channel::Sender<IndraEvent>,
}

impl Ws {
    pub fn new(config: WsConfig) -> Self {
        let s1: async_channel::Sender<IndraEvent>;
        let r1: async_channel::Receiver<IndraEvent>;
        (s1, r1) = async_channel::unbounded();
        Ws {
            config: config.clone(),
            receiver: r1,
            sender: s1,
        }
    }
}

impl AsyncTaskReceiver for Ws {
    async fn async_sender(self) {
        println!("IndraTask Ws::sender");
    }
}

impl AsyncTaskSender for Ws {
    async fn async_receiver(self, _sender: async_channel::Sender<IndraEvent>) {
        println!("IndraTask Ws::receiver");
    }
}
