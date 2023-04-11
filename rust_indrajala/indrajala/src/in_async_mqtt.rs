//use std::time::Duration;
// mod in_async_mqtt;

use paho_mqtt::{AsyncClient, CreateOptionsBuilder}; // , Message};

pub async fn mq(broker: String) {
    let create_opts = CreateOptionsBuilder::new()
        .server_uri(broker)
        .client_id("rust-mqtt")
        .finalize();

    let client = AsyncClient::new(create_opts).unwrap_or_else(|err| {
        println!("Error creating the client: {:?}", err);
        std::process::exit(1);
    });
    client.connect(None).await.unwrap_or_else(|err| {
        println!("Error connecting: {:?}", err);
        std::process::exit(1);
    });
    client.subscribe("#", 0).await.unwrap();

    loop {
        client.set_message_callback(|_client, msg| {
            if let Some(msg) = msg {
                // get topic
                let topic = msg.topic();
                // get payload
                let payload = msg.payload_str();
                // check if message was retained:
                let retained = msg.retained();
                if retained {
                    // ignore! println!("Received retained message on topic: {}", topic);
                } else {
                    println!("Received message on topic: {} with payload: {}", topic, payload);
                }
            }
        });
    }
}

