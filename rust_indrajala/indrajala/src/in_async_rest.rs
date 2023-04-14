use crate::indra_config::RestConfig;
use crate::IndraEvent;
use std::time::Duration;

use crate::{AsyncTaskReceiver, AsyncTaskSender, IndraTask}; // , IndraTask} //, TaskInit};
use tide;
use tide_rustls::TlsListener;

#[derive(Clone)]
pub struct Rest {
    pub config: RestConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
    pub task: IndraTask,
}

impl Rest {
    pub fn new(config: RestConfig) -> Self {
        let s1: async_channel::Sender<IndraEvent>;
        let r1: async_channel::Receiver<IndraEvent>;
        (s1, r1) = async_channel::unbounded();
        Rest {
            config: config.clone(),
            receiver: r1,
            task: IndraTask {
                name: "Rest".to_string(),
                active: config.active,
                out_topics: config.clone().out_topics.clone(),
                out_channel: s1,
            },
        }
    }
}

impl AsyncTaskReceiver for Rest {
    async fn async_sender(self) {
        println!("IndraTask Rest::sender");
        let mut app = tide::new();
        let pt = self.config.url.as_str();
        app.at(&pt).get(|_| async { Ok("Hello TLS") });
        if self.config.ssl {
            app.listen(
                TlsListener::build()
                    .addrs(self.config.address)
                    .cert(self.config.cert)
                    .key(self.config.key),
            )
            .await
            .unwrap();
        } else {
            app.listen(self.config.address).await.unwrap();
        }
        // Ok(())
    }
}

impl AsyncTaskSender for Rest {
    async fn async_receiver(self, sender: async_channel::Sender<IndraEvent>) {
        loop {
            async_std::task::sleep(Duration::from_millis(1000)).await;
        }
    }
}
