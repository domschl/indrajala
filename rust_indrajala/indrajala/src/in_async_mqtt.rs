use async_channel;
use paho_mqtt::{AsyncClient, ConnectOptionsBuilder, CreateOptionsBuilder}; // , Message};
use std::time::Duration;
//use async_std::task;
use async_std::stream::StreamExt;

use crate::indra_config::IndraConfig;
use crate::IndraEvent;

pub async fn mq(indra_config: IndraConfig, sender: async_channel::Sender<IndraEvent>) {
    let mqtt_config = &indra_config.mqtt;
    let server_uri = format!("tcp://{}:{}", mqtt_config.host, mqtt_config.port);

    let create_opts = CreateOptionsBuilder::new()
        .server_uri(server_uri)
        .client_id(&mqtt_config.client_id)
        .finalize();

    let mut client = AsyncClient::new(create_opts).unwrap_or_else(|err| {
        println!("Error creating the client: {:?}", err);
        std::process::exit(1);
    });

    let mut strm = client.get_stream(25);
    let conn_opts = ConnectOptionsBuilder::new()
        .user_name(&mqtt_config.username)
        .password(&mqtt_config.password)
        .finalize();

    client.connect(conn_opts).await.unwrap_or_else(|err| {
        println!("Error connecting: {:?}", err);
        std::process::exit(1);
    });
    let qos = vec![0; mqtt_config.topics.len()];
    client
        .subscribe_many(&mqtt_config.topics, &qos)
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
                let mut dd = IndraEvent::new();
                dd.domain = topic.to_string();
                dd.data = serde_json::json!(payload.to_string());
                sender.send(dd).await.unwrap();
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

pub async fn mq_send(_ie: IndraEvent) {}
