use async_channel;
use paho_mqtt::{AsyncClient, ConnectOptionsBuilder, CreateOptionsBuilder};
use std::time::Duration;
//use async_std::task;
use async_std::stream::StreamExt;
use uuid::Uuid;

use crate::indra_config::MqttConfig;
use crate::IndraEvent;
use crate::{AsyncTaskReceiver, AsyncTaskSender};

#[derive(Clone)]
pub struct Mqtt {
    pub config: MqttConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
    pub sender: async_channel::Sender<IndraEvent>,
}

impl Mqtt {
    pub fn new(config: MqttConfig) -> Self {
        let s1: async_channel::Sender<IndraEvent>;
        let r1: async_channel::Receiver<IndraEvent>;
        (s1, r1) = async_channel::unbounded();
        Mqtt {
            config: config.clone(),
            receiver: r1,
            sender: s1,
        }
    }
}

impl AsyncTaskSender for Mqtt {
    async fn async_sender(self, sender: async_channel::Sender<IndraEvent>) {
        let server_uri = format!("tcp://{}:{}", self.config.host, self.config.port);
        let client_id = format!("{}_{}", &self.config.client_id, Uuid::new_v4().to_string());
        let create_opts = CreateOptionsBuilder::new()
            .server_uri(server_uri)
            .client_id(client_id)
            .finalize();

        let mut client = AsyncClient::new(create_opts).unwrap_or_else(|err| {
            println!("Error creating the client: {:?}", err);
            std::process::exit(1);
        });

        let mut strm = client.get_stream(25);
        let conn_opts = ConnectOptionsBuilder::new()
            .user_name(&self.config.username)
            .password(&self.config.password)
            .finalize();

        client.connect(conn_opts).await.unwrap_or_else(|err| {
            println!("Error connecting: {:?}", err);
            std::process::exit(1);
        });
        let qos = vec![0; self.config.topics.len()];
        client
            .subscribe_many(&self.config.topics, &qos)
            .await
            .unwrap();

        while let Some(msg_opt) = strm.next().await {
            if let Some(msg) = msg_opt {
                // get topic
                let topic = msg.topic();
                // get payload
                let payload = msg.payload_str();
                // check if message was retained:
                let retained = msg.retained();
                if retained {
                    // ignore! println!("Received retained message on topic: {}", topic);
                } else {
                    if self.config.active {
                        let mut dd = IndraEvent::new();
                        dd.domain = topic.to_string();
                        dd.from_instance = self.config.name.clone();
                        dd.data = serde_json::json!(payload.to_string());
                        sender.send(dd).await.unwrap();
                    }
                }
                // println!("{}", msg);
            } else {
                // A "None" means we were disconnected. Try to reconnect...
                println!("Lost connection. Attempting reconnect.");
                while let Err(err) = client.reconnect().await {
                    println!("Error reconnecting: {}", err);
                    // For tokio use: tokio::time::delay_for()
                    async_std::task::sleep(Duration::from_millis(1000)).await;
                }
            }
        }

        // Explicit return type for the async block
        //Ok::<(), mqtt::Error>(())
    }
}

impl AsyncTaskReceiver for Mqtt {
    async fn async_receiver(self) {
        let _msg = self.receiver.recv().await;
        if self.config.active {
            // println!("MQTT::sender (publisher): {:?}", msg);
        }
    }
}
