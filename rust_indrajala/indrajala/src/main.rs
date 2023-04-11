//use std::time::Duration;
use async_std::task;
use paho_mqtt::{AsyncClient, CreateOptionsBuilder}; // , Message};

async fn mq() {
    let create_opts = CreateOptionsBuilder::new()
        .server_uri("tcp://nalanda.fritz.box:1883")
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
                println!("Received message on topic: {} with payload: {}", topic, payload);
            }
        });
    }
    //loop {
    //    if let Some(msg) = client.try_receive(Duration::from_millis(100)).unwrap() {
    //        println!("Received message {:?}", msg);
    //    }
    // }
}

fn main() {
    task::block_on(mq());
}
