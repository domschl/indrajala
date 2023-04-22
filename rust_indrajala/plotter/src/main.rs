use std::{thread, time};
use tungstenite::{connect, Message};
use url::Url;

use indra_event::IndraEvent;

// Create a websocket connection to a server that sends records
fn main() {
    let (mut socket, _response) =
        connect(Url::parse("ws://localhost:8082").unwrap()).expect("Should work.");
    println!("Connected to the server");

    let mut f = 1.0;
    let delta = time::Duration::from_millis(500);
    let ie: IndraEvent = IndraEvent::new();
    let ie_txt = ie.to_json().unwrap();
    socket.write_message(ie_txt.into()).unwrap();
    println!("sent message");
    // Loop over the messages from the server
    while let Ok(msg) = socket.read_message() {
        // If the message is text, parse it as a record
        if let Message::Text(text) = msg {
            println!("Received: {}", text);
            f += 1.0;
            thread::sleep(delta);
            socket.write_message(format!("1.0, {}", f).into()).unwrap();
        }
    }
}
