//use std::f64::{partial_max, partial_min};
use chrono::{DateTime, Utc};
//use glib;
use gtk::prelude::*;
use gtk::{
    Application, ApplicationWindow, Box, DrawingArea, Label, ListBox, PolicyType, ScrolledWindow,
};
use partial_min_max::{max, min};
use serde::Deserialize;
use std::collections::HashMap;
use std::fs;
use std::sync::{Arc, Mutex};
use std::thread;
//use toml;
use tungstenite::{connect, Message};
use url::Url;

use plotters::drawing::IntoDrawingArea;
use plotters::prelude::*;
use plotters::style::WHITE;
//{ChartBuilder, IntoDrawingArea, LabelAreaPosition, LineSeries};
use plotters_cairo::CairoBackend;

use indra_event::{
    IndraEvent, IndraHistoryRequest, IndraHistoryRequestMode, IndraUniqueDomainsRequest,
};

//use std::time;
//use chrono::prelude::*;
//use std::time::Duration;
//use plotters::prelude::*;

//fn tconv(t: chrono::DateTime<Utc>) -> chrono::DateTime<Utc> {
//    return t;
//}

#[derive(Deserialize, Clone, Debug)]
struct Config {
    uris: Vec<String>,
    default_domains: Vec<String>,
}

impl Config {
    fn new(config_filename: &str) -> Config {
        let toml_string = fs::read_to_string(config_filename).unwrap();
        let toml_str = toml_string.as_str();

        let cfg: Config = toml::from_str(toml_str).unwrap();
        cfg
    }
    fn _add_uri(&mut self, uri: String) {
        self.uris.push(uri);
    }
}

fn build_ui(app: &Application) {
    //println!("build_ui");
    let cfg: Config = Config::new("plotter.toml");
    // let init_time_series: Hashmap<String, Vec<(DateTime<Local>, f64)>> = Hashmap::new();
    let init_time_series: HashMap<String, Vec<(DateTime<Utc>, f64)>> = HashMap::new();
    let time_series = Arc::new(Mutex::new(init_time_series));
    // Create a window and set the title
    enum ChMessage {
        UpdateListBox(String),
        UpdateGraph(),
    }

    let list_box1 = ListBox::new();
    let scrolled_window1 = ScrolledWindow::builder()
        .hscrollbar_policy(PolicyType::Never) // Disable horizontal scrolling
        .min_content_width(360)
        .min_content_height(200)
        .child(&list_box1)
        .build();
    let list_box2 = ListBox::new();
    let scrolled_window2 = ScrolledWindow::builder()
        .hscrollbar_policy(PolicyType::Never) // Disable horizontal scrolling
        .min_content_width(360)
        .min_content_height(300)
        .child(&list_box2)
        .build();
    let list_box3 = ListBox::new();
    let scrolled_window3 = ScrolledWindow::builder()
        .hscrollbar_policy(PolicyType::Never) // Disable horizontal scrolling
        .min_content_width(360)
        .child(&list_box3)
        .build();

    let (sender, receiver) = glib::MainContext::channel(glib::PRIORITY_DEFAULT);
    let label = Label::new(Some("Hello World!"));
    label.set_width_request(200);

    let box_h: Box = Box::new(gtk::Orientation::Horizontal, 0);
    let box_v = Box::new(gtk::Orientation::Vertical, 0);
    box_v.set_width_request(200);
    let drawing_area = DrawingArea::new(); // builder().build(); // DrawingArea::new();
    drawing_area.set_content_width(1000);
    let lb2 = list_box2.clone();
    drawing_area.set_draw_func({
        let shared_time = Arc::clone(&time_series);
        move |_, cr, w, h| {
            let backend = CairoBackend::new(cr, (w as u32, h as u32)).unwrap();
            let root_area = backend.into_drawing_area();
            root_area.fill(&WHITE).unwrap();

            // plot time_series
            let time_series_lock = shared_time.lock().unwrap();

            if time_series_lock.len() < 1 {
                println!("nothing in time_series");
                return;
            }
            if lb2.selected_row().is_none() {
                println!("nothing selected in time_series");
                return;
            }
            let selected_row = lb2.selected_row().unwrap();
            let selected_row_label = selected_row
                .child()
                .unwrap()
                .downcast::<Label>()
                .unwrap()
                .label()
                .to_string();
            let data_vec = time_series_lock.get(&selected_row_label).unwrap();
            if data_vec.len() < 2 {
                println!(
                    "selected {} in time_series contains not yet enough data",
                    selected_row_label
                );
                return;
            }
            let (min_datetime, min_f64) = data_vec
                .iter()
                .fold((data_vec[0].0, data_vec[0].1), |acc, val| {
                    (min(acc.0, val.0), min(acc.1, val.1))
                });
            let (max_datetime, max_f64) = data_vec
                .iter()
                .fold((data_vec[0].0, data_vec[0].1), |acc, val| {
                    (max(acc.0, val.0), max(acc.1, val.1))
                });

            let mut ctx = ChartBuilder::on(&root_area)
                .set_label_area_size(LabelAreaPosition::Left, 100)
                .set_label_area_size(LabelAreaPosition::Bottom, 40)
                .caption("Indrajala/muWerk Temperature", ("sans-serif", 14))
                .build_cartesian_2d(min_datetime..max_datetime, min_f64 as f32..max_f64 as f32)
                .unwrap();

            ctx.configure_mesh().x_labels(6).draw().unwrap();
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
                data_vec.iter().map(|d| (d.0, d.1 as f32)),
                &RED,
            ))
            .unwrap();
        }
    });

    box_h.append(&box_v);
    box_h.append(&drawing_area);
    box_v.append(&label);
    box_v.append(&scrolled_window1);
    box_v.append(&scrolled_window2);
    box_v.append(&scrolled_window3);

    let window = ApplicationWindow::builder()
        .application(app)
        .title("Indrajala Event Plotter")
        .default_width(1200)
        .default_height(600)
        .child(&box_h)
        .build();

    let host2 = cfg.uris[0].clone();
    let domain_topic2 = cfg.default_domains.clone();
    thread::spawn({
        //websocket_client
        let shared_time_series = Arc::clone(&time_series);
        move || {
            //let mut known_topics: Vec<String> = Vec::new();
            let (mut socket, _response) =
                connect(Url::parse(host2.as_str()).unwrap()).expect("Should work.");
            println!("Connected to the server");

            //let delta = time::Duration::from_millis(500);
            let mut ie: IndraEvent = IndraEvent::new();
            ie.domain = "$cmd/subs".to_string();
            ie.from_id = "ws/plotter".to_string();
            ie.data_type = "vector/string".to_string();
            // It is not redundant.
            #[allow(clippy::redundant_clone)]
            let subs: Vec<String> = domain_topic2.clone();
            ie.data = serde_json::to_string(&subs).unwrap();
            let ie_txt = serde_json::to_string(&ie).unwrap();
            socket.write_message(ie_txt.into()).unwrap();
            println!("sent message $cmd/subs");
            let mut ie: IndraEvent = IndraEvent::new();
            ie.domain = "$trx/db/req/uniquedomains".to_string();
            let hr: IndraUniqueDomainsRequest = IndraUniqueDomainsRequest {
                domain: Some("$event/%".to_string()),
                data_type: Some("number/float%".to_string()),
            };
            ie.from_id = "ws/plotter".to_string();
            ie.data_type = "uniquedomainsrequest".to_string();
            ie.data = serde_json::to_string(&hr).unwrap();
            let ie_txt = serde_json::to_string(&ie).unwrap();
            socket.write_message(ie_txt.into()).unwrap();
            println!("sent message req/uniquedomains");
            // Loop over the messages from the server
            while let Ok(msg) = socket.read_message() {
                // If the message is text, parse it as a record
                if let Message::Text(text) = msg {
                    //println!("Received: len={}", text.len());
                    let ier: IndraEvent = serde_json::from_str(text.as_str()).unwrap();
                    // if ier.domain.starts_with("$event/") {
                    //     ier.domain = ier.domain.replace("$event/", "");
                    //}
                    println!("Received: {}", ier.domain);
                    let mut matched = false;
                    let mut reply = false;
                    for domain in cfg.default_domains.iter() {
                        if IndraEvent::mqcmp(ier.domain.as_str(), domain.as_str()) {
                            matched = true;
                            reply = false;
                        }
                    }
                    if !matched {
                        let mut st = ier.domain.clone();
                        st.truncate(2);
                        st = st.to_lowercase();
                        if st == *"ws" {
                            matched = true;
                            reply = true;
                        }
                    }
                    if matched {
                        if !reply {
                            let time = IndraEvent::julian_to_datetime(ier.time_jd_start); //.with_timezone(&Local);
                            if !ier.data_type.starts_with("number/float") {
                                continue;
                            }

                            let domain = ier.domain.clone();
                            //let num_text: String = ier.data.to_string().replace("\"", "");
                            //let value_opt = num_text.trim().parse();
                            let value_opt: Result<f64, serde_json::Error> =
                                serde_json::from_str(ier.data.as_str());
                            let value = value_opt.unwrap();
                            println!("domain: >{}<, value: {}", domain, value);
                            let mut time_series_lock = shared_time_series.lock().unwrap();
                            // time_series_lock.push((time.with_timezone(&Local), value));
                            if let std::collections::hash_map::Entry::Vacant(e) =
                                time_series_lock.entry(domain.clone())
                            {
                                e.insert(Vec::new());
                                time_series_lock
                                    .get_mut(domain.as_str())
                                    .unwrap()
                                    .push((time, value));
                                Arc::new(&sender)
                                    .send(ChMessage::UpdateListBox(domain.clone()))
                                    .unwrap();
                                // request history
                                let mut ie: IndraEvent = IndraEvent::new();
                                ie.domain = "$trx/db/req/history".to_string();
                                ie.from_id = "ws/plotter".to_string();
                                ie.data_type = "historyrequest".to_string();
                                let req: IndraHistoryRequest = IndraHistoryRequest {
                                    domain: domain.clone(),
                                    mode: IndraHistoryRequestMode::Sample,
                                    data_type: "number/float".to_string(),
                                    time_jd_start: None,
                                    time_jd_end: None,
                                    limit: Some(1000),
                                };
                                ie.data = serde_json::to_string(&req).unwrap();
                                let ie_txt = serde_json::to_string(&ie).unwrap();
                                socket.write_message(ie_txt.into()).unwrap();
                                println!("sent message request history of {}", domain);
                            } else {
                                time_series_lock
                                    .get_mut(domain.as_str())
                                    .unwrap()
                                    .push((time, value));
                            }
                            // println!("Temperature at {}: {}", time, value);
                            /*
                            if !known_topics.contains(&domain.clone()) {
                                known_topics.push(domain.clone());
                                Arc::new(&sender)
                                    .send(ChMessage::UpdateListBox(domain.clone()))
                                    .unwrap();
                            }
                            */
                        } else {
                            println!(
                                "We got some reply! {} {} for {}: {}",
                                ier.domain, ier.from_id, ier.to_scope, ier.data_type
                            );
                            if ier.data_type == "vector/tuple/jd/float" {
                                let domain: String = ier.to_scope.to_string();
                                let res: Vec<(f64, f64)> =
                                    serde_json::from_str(ier.data.to_string().as_str()).unwrap();
                                println!("res: {}", res.len());
                                println!(
                                    "History DB Transaction time: {}",
                                    ier.time_jd_end.unwrap() - ier.time_jd_start
                                );

                                let mut time_series_lock = shared_time_series.lock().unwrap();
                                if time_series_lock.contains_key(&domain.clone()) {
                                    for r in res.iter() {
                                        time_series_lock
                                            .get_mut(domain.as_str())
                                            .unwrap()
                                            .push((IndraEvent::julian_to_datetime(r.0), r.1));
                                    }
                                    // sort array
                                    let arr = time_series_lock.get_mut(domain.as_str()).unwrap();
                                    arr.sort_by(|a, b| a.0.cmp(&b.0));
                                    let arr2 = &mut arr
                                        .windows(2)
                                        .filter_map(|w| {
                                            if w[0].0 == w[1].0 {
                                                None
                                            } else {
                                                Some(w[0])
                                            }
                                        })
                                        .chain(arr.last().cloned())
                                        .collect::<Vec<(DateTime<Utc>, f64)>>();
                                    if arr.len() != arr2.len() {
                                        println!(
                                            "XXXXXXX arr: {}, arr2: {}",
                                            arr.len(),
                                            arr2.len()
                                        );
                                    } else {
                                        println!("XYX no dups");
                                    }
                                    arr.clear();
                                    arr.append(arr2);
                                } else {
                                    println!("Can't find {}", domain.clone());
                                }
                                continue;
                            } else if ier.data_type.starts_with("vector/string") {
                                println!("UNIQUE reply! {}.", ier.data_type);
                                println!(
                                    "UNIQUE DOMAIN DB Transaction time: {}",
                                    ier.time_jd_end.unwrap() - ier.time_jd_start
                                );
                                let domains: Vec<String> =
                                    serde_json::from_str(ier.data.as_str()).unwrap(); //.to_string().as_str()).unwrap();
                                let mut time_series_lock = shared_time_series.lock().unwrap();
                                for domain in domains.iter() {
                                    let mut matched = false;
                                    for sub in domain_topic2.iter() {
                                        if IndraEvent::mqcmp(domain, sub) {
                                            matched = true;
                                            break;
                                        }
                                    }
                                    if !matched {
                                        continue;
                                    }
                                    if let std::collections::hash_map::Entry::Vacant(e) =
                                        time_series_lock.entry(domain.clone())
                                    {
                                        e.insert(Vec::new());
                                        Arc::new(&sender)
                                            .send(ChMessage::UpdateListBox(domain.clone()))
                                            .unwrap();
                                        // request history
                                        let mut ie: IndraEvent = IndraEvent::new();
                                        ie.domain = "$trx/db/req/history".to_string();
                                        ie.from_id = "ws/plotter".to_string();
                                        ie.data_type = "eventhistory".to_string();
                                        let req: IndraHistoryRequest = IndraHistoryRequest {
                                            domain: domain.clone(),
                                            mode: IndraHistoryRequestMode::Sample,
                                            data_type: "number/float%".to_string(),
                                            time_jd_start: None,
                                            time_jd_end: None,
                                            limit: Some(1000),
                                        };
                                        ie.data = serde_json::to_string(&req).unwrap();
                                        let ie_txt = serde_json::to_string(&ie).unwrap();
                                        socket.write_message(ie_txt.into()).unwrap();
                                        println!("sent message request history of {}", domain);
                                    }
                                }
                            } else {
                                println!("Unknown reply type: {}", ier.data_type);
                            }
                        }
                        // Check if text in known_topics:
                        if matched {
                            Arc::new(&sender).send(ChMessage::UpdateGraph()).unwrap();
                        }
                    }
                }
            }
        }
    });
    let listbox_clone2 = list_box2;
    //let time_series_clone = time_series.clone();
    let drawing_area_clone = drawing_area;
    receiver.attach(None, move |msg| {
        match msg {
            ChMessage::UpdateListBox(text) => listbox_clone2.append(&Label::new(Some(&text))),
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
