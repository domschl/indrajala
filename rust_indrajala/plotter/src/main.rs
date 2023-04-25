//use std::f64::{partial_max, partial_min};
use partial_min_max::{max, min};
use std::sync::{Arc, Mutex};
use std::thread;

use chrono::{DateTime, Local, Utc};
use glib;
use gtk::prelude::*;
use gtk::{
    Application, ApplicationWindow, Box, DrawingArea, Label, ListBox, PolicyType, ScrolledWindow,
};
use tungstenite::{connect, Message};
use url::Url;

use plotters::drawing::IntoDrawingArea;
use plotters::prelude::*;
use plotters::style::WHITE;
//{ChartBuilder, IntoDrawingArea, LabelAreaPosition, LineSeries};
use plotters_cairo::CairoBackend;

use indra_event::IndraEvent;

//use std::time;
//use chrono::prelude::*;
//use std::time::Duration;
//use plotters::prelude::*;

fn build_ui(app: &Application) {
    // let init_time_series: Vec<(DateTime<Local>, f64)> = Vec::new();
    let init_time_series: Vec<(DateTime<Utc>, f64)> = Vec::new();
    let time_series = Arc::new(Mutex::new(init_time_series));
    // Create a window and set the title
    enum ChMessage {
        UpdateListBox(String),
        UpdateGraph(),
    }
    let list_box = ListBox::new();

    let scrolled_window = ScrolledWindow::builder()
        .hscrollbar_policy(PolicyType::Never) // Disable horizontal scrolling
        .min_content_width(360)
        .child(&list_box)
        .build();

    let (sender, receiver) = glib::MainContext::channel(glib::PRIORITY_DEFAULT);
    let label = Label::new(Some("Hello World!"));

    let box2: Box = Box::new(gtk::Orientation::Horizontal, 0);
    let drawing_area = DrawingArea::new(); // builder().build(); // DrawingArea::new();
    drawing_area.set_content_width(1000);
    drawing_area.set_draw_func({
        let shared_time = Arc::clone(&time_series);
        move |_, cr, w, h| {
            let backend = CairoBackend::new(cr, (w as u32, h as u32)).unwrap();
            let root_area = backend.into_drawing_area();
            root_area.fill(&WHITE).unwrap();

            // plot time_series
            let time_series_lock = shared_time.lock().unwrap();

            if time_series_lock.len() < 2 {
                return;
            }
            let (min_datetime, min_f64) = time_series_lock.iter().fold(
                (time_series_lock[0].0, time_series_lock[0].1),
                |acc, val| (min(acc.0, val.0), min(acc.1, val.1)),
            );
            let (max_datetime, max_f64) = time_series_lock.iter().fold(
                (time_series_lock[0].0, time_series_lock[0].1),
                |acc, val| (max(acc.0, val.0), max(acc.1, val.1)),
            );

            let mut ctx = ChartBuilder::on(&root_area)
                .set_label_area_size(LabelAreaPosition::Left, 40)
                .set_label_area_size(LabelAreaPosition::Bottom, 40)
                .caption("Indrajala/muWerk Temperature", ("sans-serif", 14))
                .build_cartesian_2d(min_datetime..max_datetime, min_f64 as f32..max_f64 as f32)
                .unwrap();

            ctx.configure_mesh().draw().unwrap();
            /*
                ctx.draw_series(LineSeries::new(
                    time_series_lock
                        .iter()
                        .map(|d| (d.0.timestamp() as i32 % 100, d.1 as i32 % 100)),
                    &RED,
                ))
                .unwrap();
            */
            ctx.draw_series(LineSeries::new(
                time_series_lock.iter().map(|d| (d.0, d.1 as f32)),
                &RED,
            ))
            .unwrap();
        }
    });

    box2.append(&drawing_area);
    box2.append(&scrolled_window);
    box2.append(&label);

    let window = ApplicationWindow::builder()
        .application(app)
        .title("Indrajala Event Plotter")
        .default_width(1200)
        .default_height(600)
        .child(&box2)
        .build();

    thread::spawn({
        let shared_time_series = Arc::clone(&time_series);
        move || {
            let (mut socket, _response) =
                connect(Url::parse("ws://localhost:8082").unwrap()).expect("Should work.");
            println!("Connected to the server");

            //let delta = time::Duration::from_millis(500);
            let mut ie: IndraEvent = IndraEvent::new();
            ie.domain = "$cmd/ws/subs".to_string();
            ie.from_instance = "ws/plotter".to_string();
            ie.data_type = "cmd".to_string();
            ie.data = serde_json::from_str(r#"{"subs":["omu/enviro-master/BME280-1/sensor/#"]}"#)
                .unwrap();
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
                    let value: f64 = text.trim().parse().unwrap();
                    let mut time_series_lock = shared_time_series.lock().unwrap();
                    // time_series_lock.push((time.with_timezone(&Local), value));
                    time_series_lock.push((time, value));

                    Arc::new(&sender)
                        .send(ChMessage::UpdateListBox(text.clone()))
                        .unwrap();

                    Arc::new(&sender).send(ChMessage::UpdateGraph()).unwrap();

                    println!("Temperature at {}: {}", time, value);
                }
            }
        }
    });
    let listbox_clone = list_box.clone();
    //let time_series_clone = time_series.clone();
    let drawing_area_clone = drawing_area.clone();
    receiver.attach(None, move |msg| {
        match msg {
            ChMessage::UpdateListBox(text) => listbox_clone.append(&Label::new(Some(&text))),
            ChMessage::UpdateGraph() => {
                drawing_area_clone.queue_draw();
            }
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
    const APP_ID: &str = "org.gtk_rs.IndrajalaClient";

    // Create a new application
    let app = Application::builder().application_id(APP_ID).build();

    // Connect to "activate" signal of `app`
    app.connect_activate(build_ui);

    // Run the application
    app.run();
}
