//use std::time;
use chrono::prelude::*;
use tungstenite::{connect, Message};
use url::Url;

use indra_event::IndraEvent;

// Create a websocket connection to a server that sends records
fn main() {
    let (mut socket, _response) =
        connect(Url::parse("ws://localhost:8082").unwrap()).expect("Should work.");
    println!("Connected to the server");

    //let delta = time::Duration::from_millis(500);
    let mut ie: IndraEvent = IndraEvent::new();
    ie.domain = "$cmd/ws/subs".to_string();
    ie.from_instance = "ws/plotter".to_string();
    ie.data_type = "cmd".to_string();
    ie.data = serde_json::from_str(r#"{"subs":["omu/enviro-master/BME280-1/sensor/#"]}"#).unwrap();
    let ie_txt = ie.to_json().unwrap();
    socket.write_message(ie_txt.into()).unwrap();
    println!("sent message");
    // Loop over the messages from the server
    while let Ok(msg) = socket.read_message() {
        // If the message is text, parse it as a record
        if let Message::Text(text) = msg {
            //println!("Received: {}", text);
            let ier: IndraEvent = IndraEvent::from_json(&text).unwrap();
            println!(
                "Temperature at {}: {}",
                IndraEvent::julian_to_datetime(ier.time_jd_start).with_timezone(&Local),
                ier.data
            );
        }
    }
}
