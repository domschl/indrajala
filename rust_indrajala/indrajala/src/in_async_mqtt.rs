//use async_channel;
use paho_mqtt::{AsyncClient, ConnectOptionsBuilder, CreateOptionsBuilder};
use std::time::Duration;
//use async_std::task;
use async_std::stream::StreamExt;
use uuid::Uuid;

//use env_logger::Env;
//use log::{debug, error, info, warn};
use log::{debug, error, warn};

use crate::indra_config::MqttConfig;
use crate::AsyncIndraTask;
use crate::IndraEvent;

#[derive(Clone)]
pub struct Mqtt {
    pub config: MqttConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
    pub sender: async_channel::Sender<IndraEvent>,
    pub subs: Vec<String>,
}

impl Mqtt {
    pub fn new(config: MqttConfig) -> Self {
        let s1: async_channel::Sender<IndraEvent>;
        let r1: async_channel::Receiver<IndraEvent>;
        (s1, r1) = async_channel::unbounded();
        let mqtt_config = config; //.clone();
        let subs = vec![format!("{}/#", mqtt_config.name)];

        Mqtt {
            config: mqtt_config,
            receiver: r1,
            sender: s1,
            subs,
        }
    }
}

impl AsyncIndraTask for Mqtt {
    async fn async_sender(self, sender: async_channel::Sender<IndraEvent>) {
        if !self.config.active {
            debug!("MQTT is not active");
            return;
        }
        let server_uri = format!("tcp://{}:{}", self.config.host, self.config.port);
        let client_id = format!("{}_{}", &self.config.client_id, Uuid::new_v4().to_string());
        let create_opts = CreateOptionsBuilder::new()
            .server_uri(server_uri)
            .client_id(client_id)
            .finalize();

        let mut client = AsyncClient::new(create_opts).unwrap_or_else(|err| {
            error!("Error creating the MQTT client: {:?}", err);
            std::process::exit(1); // XXX exit really?
        });

        let mut strm = client.get_stream(None);
        let conn_opts = ConnectOptionsBuilder::new()
            .user_name(&self.config.username)
            .password(&self.config.password)
            .finalize();

        client.connect(conn_opts).await.unwrap_or_else(|err| {
            error!("Error connecting: {:?}", err);
            std::process::exit(1); // XXX exit really?
        });
        let qos = vec![0; self.config.topics.len()];
        if self.config.active {
            client
                .subscribe_many(&self.config.topics, &qos)
                .await
                .unwrap();
        }
        while let Some(msg_opt) = strm.next().await {
            if let Some(msg) = msg_opt {
                // get topic
                let topic = msg.topic();
                // get payload
                let payload = msg.payload_str();
                // check if message was retained:
                let retained = msg.retained();
                if !retained && self.config.active {
                    let mut dd = IndraEvent::new();
                    if topic.starts_with('$') {
                        dd.domain = topic.to_string();
                    } else {
                        dd.domain = "$event/".to_string() + topic;
                    }
                    dd.domain = "$event/".to_string() + topic;
                    dd.from_id = self.config.name.clone();
                    dd.uuid4 = Uuid::new_v4().to_string();
                    dd.to_scope = self.config.to_scope.clone();
                    let num_int: Result<i64, _> = payload.trim().parse::<i64>();
                    if num_int.is_ok() {
                        dd.data_type = "number/int".to_string();
                        dd.data = num_int.unwrap().to_string();
                    } else {
                        let num_float: Result<f64, _> = payload.trim().parse::<f64>();
                        if num_float.is_ok() {
                            dd.data_type = "number/float".to_string();
                            dd.data = num_float.unwrap().to_string();
                        } else if ["on", "true", "active"]
                            .contains(&payload.trim().to_lowercase().as_str())
                        {
                            dd.data_type = "bool".to_string();
                            dd.data = true.to_string();
                        } else if ["off", "false", "inactive"]
                            .contains(&payload.trim().to_lowercase().as_str())
                        {
                            dd.data_type = "bool".to_string();
                            dd.data = false.to_string();
                        } else {
                            let val_json: Result<serde_json::Value, serde_json::Error> =
                                serde_json::from_str(payload.to_string().as_str());
                            if val_json.is_ok() {
                                dd.data_type = "json".to_string();
                                dd.data = payload.to_string();
                            } else {
                                dd.data_type = "string".to_string();
                                dd.data = payload.to_string();
                            }
                        }
                    }
                    if sender.send(dd).await.is_err() {
                        warn!("Mqtt: Error sending message to channel, assuming shutdown.");
                        break;
                    }
                }
                debug!("MQTT message: {}", msg);
            } else {
                // A "None" means we were disconnected. Try to reconnect...
                warn!("MQTT: Lost connection. Attempting reconnect.");
                while let Err(err) = client.reconnect().await {
                    debug!("MQTT Error reconnecting: {}", err);
                    // For tokio use: tokio::time::delay_for()
                    async_std::task::sleep(Duration::from_millis(1000)).await;
                    debug!("MQTT: Reconnect attempt failed. Retrying...");
                }
                warn!("MQTT: Reconnected.");
                let qos = vec![0; self.config.topics.len()];
                if self.config.active {
                    client
                        .subscribe_many(&self.config.topics, &qos)
                        .await
                        .unwrap();
                }
            }
        }

        // Explicit return type for the async block
        //Ok::<(), mqtt::Error>(())
    }

    async fn async_receiver(mut self, _sender: async_channel::Sender<IndraEvent>) {
        loop {
            let msg = self.receiver.recv().await.unwrap();
            if msg.domain == "$cmd/quit" {
                debug!("Mqtt: Received quit command, quiting receive-loop.");
                self.config.active = false;
                break;
            }
            if self.config.active {
                debug!("MQTT::sender (publisher): {}", msg.domain);
            }
        }
    }
}
