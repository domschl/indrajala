use paho_mqtt::{AsyncClient, CreateOptionsBuilder}; // , Message};
use async_channel;
use std::time::Duration;
use async_std::task;
use async_std::stream::StreamExt;

pub async fn mq(broker: String, sender: async_channel::Sender<String>) {
    let create_opts = CreateOptionsBuilder::new()
        .server_uri(broker)
        .client_id("rust-mqtt")
        .finalize();

    let mut client = AsyncClient::new(create_opts).unwrap_or_else(|err| {
        println!("Error creating the client: {:?}", err);
        std::process::exit(1);
    });
    let mut strm = client.get_stream(25);
    client.connect(None).await.unwrap_or_else(|err| {
        println!("Error connecting: {:?}", err);
        std::process::exit(1);
    });
    client.subscribe("#", 0).await.unwrap();

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
                sender.send(payload.to_string()).await;
                // task::block_on(sender.send(payload.to_string())); // .await;
                println!("Received message on topic: {} with payload: {}", topic, payload);
            }
            // println!("{}", msg);
        }
        else {
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




/* 


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
                    //sender.try_send(payload.unwrap().to_string());
                    // task::block_on(sender.send(payload.to_string())); // .await;
                    println!("Received message on topic: {} with payload: {}", topic, payload);
                }
            }
        });
    }
}

*/