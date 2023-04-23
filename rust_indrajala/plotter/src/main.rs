//use std::time;
use chrono::prelude::*;
use chrono::{DateTime, Utc};
use plotters::prelude::*;
use std::time::Duration;

use tungstenite::{connect, Message};
use url::Url;

use indra_event::IndraEvent;

// Create a websocket connection to a server that sends records
fn main() {
    let root = BitMapBackend::new("plot.png", (640, 480)).into_drawing_area();
    root.fill(&WHITE);
    let root = root.margin(10, 10, 10, 10);
    // After this point, we should be able to construct a chart context
    let mut chart = ChartBuilder::on(&root)
        // Set the caption of the chart
        .caption("This is our first plot", ("sans-serif", 40).into_font())
        // Set the size of the label region
        .x_label_area_size(20)
        .y_label_area_size(40)
        // Finally attach a coordinate on the drawing area and make a chart context
        .build_cartesian_2d(0f32..10f32, 0f32..10f32)
        .unwrap();

    // Then we can draw a mesh
    chart
        .configure_mesh()
        // We can customize the maximum number of labels allowed for each axis
        .x_labels(5)
        .y_labels(5)
        // We can also change the format of the label text
        .y_label_formatter(&|x| format!("{:.3}", x))
        .draw()
        .unwrap();

    // And we can draw something in the drawing area
    chart
        .draw_series(LineSeries::new(
            vec![(0.0, 0.0), (5.0, 5.0), (8.0, 7.0)],
            &RED,
        ))
        .unwrap();
    // Similarly, we can draw point series
    chart
        .draw_series(PointSeries::of_element(
            vec![(0.0, 0.0), (5.0, 5.0), (8.0, 7.0)],
            5,
            &RED,
            &|c, s, st| {
                return EmptyElement::at(c)    // We want to construct a composed element on-the-fly
                + Circle::new((0,0),s,st.filled()) // At this point, the new pixel coordinate is established
                + Text::new(format!("{:?}", c), (10, 0), ("sans-serif", 10).into_font());
            },
        ))
        .unwrap();
    root.present().unwrap();
    //Ok(())
    let mut time_series: Vec<(DateTime<Utc>, f32)> = Vec::new();

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
            let time = IndraEvent::julian_to_datetime(ier.time_jd_start); //.with_timezone(&Local);
            let text: String = ier.data.to_string();
            let value: f32 = text.parse().unwrap_or(0.0) as f32;
            println!("Temperature at {}: {}", time, value);
            time_series.push((time, value));

            // Extract the time and value vectors from the DynElement
            let (times, values): (Vec<DateTime<Utc>>, Vec<f32>) =
                time_series.iter().map(|(t, v)| (*t, *v)).unzip();
        }
    }
}
