use std::sync::Arc;
use std::thread;

use chrono::{DateTime, Utc};
use gtk::prelude::*;
use gtk::{Application, ApplicationWindow, Label, ListBox, PolicyType, ScrolledWindow};
use tungstenite::{connect, Message};
use url::Url;

use indra_event::IndraEvent;

//use std::time;
//use chrono::prelude::*;
//use std::time::Duration;
//use plotters::prelude::*;

fn build_ui(app: &Application) {
    // Create a window and set the title
    enum ChMessage {
        UpdateListBox(String),
    }
    let list_box = ListBox::new();

    let scrolled_window = ScrolledWindow::builder()
        .hscrollbar_policy(PolicyType::Never) // Disable horizontal scrolling
        .min_content_width(360)
        .child(&list_box)
        .build();

    let (sender, receiver) = glib::MainContext::channel(glib::PRIORITY_DEFAULT);

    let window = ApplicationWindow::builder()
        .application(app)
        .title("My GTK App")
        .default_width(600)
        .default_height(300)
        .child(&scrolled_window)
        .build();

    thread::spawn(move || {
        let mut time_series: Vec<(DateTime<Utc>, f64)> = Vec::new();

        let (mut socket, _response) =
            connect(Url::parse("ws://localhost:8082").unwrap()).expect("Should work.");
        println!("Connected to the server");

        //let delta = time::Duration::from_millis(500);
        let mut ie: IndraEvent = IndraEvent::new();
        ie.domain = "$cmd/ws/subs".to_string();
        ie.from_instance = "ws/plotter".to_string();
        ie.data_type = "cmd".to_string();
        ie.data =
            serde_json::from_str(r#"{"subs":["omu/enviro-master/BME280-1/sensor/#"]}"#).unwrap();
        let ie_txt = ie.to_json().unwrap();
        socket.write_message(ie_txt.into()).unwrap();
        println!("sent message");
        // Loop over the messages from the server
        while let Ok(msg) = socket.read_message() {
            // If the message is text, parse it as a record
            if let Message::Text(text) = msg {
                //println!("Received: {}", text);
                let ier: IndraEvent = IndraEvent::from_json(&text).unwrap();
                let time = IndraEvent::julian_to_datetime(ier.time_jd_start); //.with_timezone(&Local);
                let text: String = ier.data.to_string().replace("\"", "");
                println!("text: >{}<", text);

                Arc::new(&sender)
                    .send(ChMessage::UpdateListBox(text.clone()))
                    .unwrap();

                let value: f64 = text.trim().parse().unwrap();
                println!("Temperature at {}: {}", time, value);
                time_series.push((time, value));
            }
        }
    });
    let listbox_clone = list_box.clone();
    receiver.attach(None, move |msg| {
        match msg {
            ChMessage::UpdateListBox(text) => listbox_clone.append(&Label::new(Some(&text))),
        }
        // Returning false here would close the receiver
        // and have senders fail
        glib::Continue(true)
    });

    // Present window
    window.present();
}

// Create a websocket connection to a server that sends records
fn main() {
    const APP_ID: &str = "org.gtk_rs.HelloWorld1";

    // Create a new application
    let app = Application::builder().application_id(APP_ID).build();

    // Connect to "activate" signal of `app`
    app.connect_activate(build_ui);

    // Run the application
    app.run();
}
