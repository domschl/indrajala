// WARNING: async fn in trait is experimental, requires nightly, but nightly beyond 2023-05-01 will
// break llm's dependencies, so for now we lock to nightly-2021-05-01, using either of these:
// rustup override set nightly-2023-05-01-x86_64-unknown-linux-gnu
// rustup override set nightly-2023-05-01-aarch64-apple-darwin

#![allow(incomplete_features)]
#![feature(async_fn_in_trait)]
#![feature(async_closure)]
// avoid boxing: (exp!)
#![feature(type_alias_impl_trait)]

//use env_logger::Env;
use flexi_logger::{
    colored_detailed_format, detailed_format, Age, Cleanup, Criterion, Duplicate, FileSpec,
    LevelFilter, Logger, Naming, WriteMode,
};
use log::{debug, error, info, warn};
use std::fs;
use std::str::FromStr;
//use std::path::Path;

//use async_channel;
use async_std::task;
use reqwest::blocking::get;
use std::thread;
use std::time::{Duration, Instant};

//mod OLD_indra_event;
use indra_event::IndraEvent;
mod indra_config;
use indra_config::IndraConfig;

mod ding_dong;
use ding_dong::DingDong;
mod in_async_mqtt;
use in_async_mqtt::Mqtt;
mod in_async_web;
use in_async_web::Web;
mod in_async_sqlx;
use in_async_sqlx::SQLx;
mod in_async_ws;
use in_async_ws::Ws; // {init_websocket_server, Ws};
mod in_async_signal;
use in_async_signal::Signal;
mod in_async_tasker;
use in_async_tasker::Tasker;
mod in_async_llm;
use in_async_llm::Llm;

#[derive(Clone)]
enum IndraTask {
    Mqtt(Mqtt),
    Web(Web),
    DingDong(DingDong),
    SQLx(SQLx),
    Ws(Ws),
    Signal(Signal),
    Tasker(Tasker),
    Llm(Llm),
}

trait AsyncIndraTask {
    //async fn async_init(self) -> Vec<String>;
    async fn async_sender(self, sender: async_channel::Sender<IndraEvent>);
    async fn async_receiver(self, sender: async_channel::Sender<IndraEvent>);
}

async fn router(mut tsk: Vec<IndraTask>, receiver: async_channel::Receiver<IndraEvent>) {
    let mut quit_cmd_received: bool = false;
    loop {
        let msg = receiver.recv().await;
        if msg.is_err() {
            error!("ERROR: router: {:?}", msg);
            continue;
        }
        let ie = msg.unwrap();
        let mut from_ident = false;
        if ie.from_id.is_empty() {
            error!(
                "ERROR: ignoring route to {}, from_id is not set: {}, can't avoid recursion.",
                ie.domain, ie.from_id
            );
        }
        let task_name = if ie.from_id == "$trx/echo" {
            ie.domain.split('/').collect::<Vec<&str>>()[0]
        } else {
            ie.from_id.split('/').collect::<Vec<&str>>()[0]
        };
        debug!("IE-Event: {} {} {}", ie.time_jd_start, ie.domain, ie.data);
        for task in &mut tsk {
            let subs;
            let act: bool;
            let acs: async_channel::Sender<IndraEvent>;
            let name: String;
            match task {
                IndraTask::DingDong(st) => {
                    let cfg = st.config.clone();
                    act = cfg.active;
                    acs = st.sender.clone();
                    name = cfg.name;
                    subs = st.subs.clone();
                }
                IndraTask::Mqtt(st) => {
                    act = st.config.clone().active;
                    acs = st.sender.clone();
                    name = st.config.clone().name;
                    subs = st.subs.clone();
                }
                IndraTask::Web(st) => {
                    act = st.config.clone().active;
                    acs = st.sender.clone();
                    name = st.config.clone().name;
                    subs = st.subs.clone();
                }
                IndraTask::SQLx(st) => {
                    act = st.config.clone().active;
                    acs = st.sender.clone();
                    name = st.config.clone().name;
                    subs = st.subs.clone();
                }
                IndraTask::Ws(st) => {
                    act = st.config.clone().active;
                    acs = st.sender.clone();
                    name = st.config.clone().name;
                    subs = st.subs.clone();
                }
                IndraTask::Signal(st) => {
                    act = st.config.clone().active;
                    acs = st.sender.clone();
                    name = st.config.clone().name;
                    subs = st.subs.clone();
                }
                IndraTask::Tasker(st) => {
                    act = st.config.clone().active;
                    acs = st.sender.clone();
                    name = st.config.clone().name;
                    subs = st.subs.clone();
                }
                IndraTask::Llm(st) => {
                    act = st.config.clone().active;
                    acs = st.sender.clone();
                    name = st.config.clone().name;
                    subs = st.subs.clone();
                }
            }
            if !act {
                continue;
            }
            let name_subs = name.clone() + "/#";
            if !subs.contains(&name_subs) {
                warn!(
                    "Received message from {} to {}, but {} is not subscribed to {}",
                    ie.from_id, ie.domain, name, name_subs
                );
            }
            if task_name == name {
                if ie.domain == "$cmd/quit" {
                    quit_cmd_received = true;
                }
                if ie.from_id == "$trx/echo" {
                    info!(
                        "ROUTE ECHO REPLY for Task: {}, domain: {}, from_id: {}",
                        name, ie.domain, ie.from_id
                    );
                    let _ = acs.send(ie.clone()).await;
                }
                from_ident = true;
                if ie.domain == "$cmd/subs" {
                    let subs_res: Result<Vec<String>, serde_json::Error> =
                        serde_json::from_str(ie.data.as_str());
                    if subs_res.is_ok() {
                        let mut subs = subs_res.unwrap();
                        warn!("{}: {} subs: {:?}", ie.from_id, name, subs);
                        match task {
                            IndraTask::DingDong(st) => {
                                let old_subs = st.subs.clone();
                                st.subs.append(&mut subs);
                                debug!("SUBS: {}: {:?} -> {:?}", name, old_subs, st.subs)
                            }
                            IndraTask::Mqtt(st) => {
                                let old_subs = st.subs.clone();
                                st.subs.append(&mut subs);
                                debug!("SUBS: {}: {:?} -> {:?}", name, old_subs, st.subs)
                            }
                            IndraTask::Web(st) => {
                                let old_subs = st.subs.clone();
                                st.subs.append(&mut subs);
                                debug!("SUBS: {}: {:?} -> {:?}", name, old_subs, st.subs)
                            }
                            IndraTask::SQLx(st) => {
                                let old_subs = st.subs.clone();
                                st.subs.append(&mut subs);
                                debug!("SUBS: {}: {:?} -> {:?}", name, old_subs, st.subs)
                            }
                            IndraTask::Ws(st) => {
                                let old_subs = st.subs.clone();
                                st.subs.append(&mut subs);
                                debug!("SUBS: {}: {:?} -> {:?}", name, old_subs, st.subs)
                            }
                            IndraTask::Signal(st) => {
                                let old_subs = st.subs.clone();
                                st.subs.append(&mut subs);
                                debug!("SUBS: {}: {:?} -> {:?}", name, old_subs, st.subs)
                            }
                            IndraTask::Tasker(st) => {
                                let old_subs = st.subs.clone();
                                st.subs.append(&mut subs);
                                debug!("SUBS: {}: {:?} -> {:?}", name, old_subs, st.subs)
                            }
                            IndraTask::Llm(st) => {
                                let old_subs = st.subs.clone();
                                st.subs.append(&mut subs);
                                debug!("SUBS: {}: {:?} -> {:?}", name, old_subs, st.subs)
                            }
                        }
                    } else {
                        error!("{}: {} subs: {:?}", ie.from_id, name, subs_res);
                    }
                }
                if ie.domain == "$cmd/unsubs" {
                    let subs_res: Result<Vec<String>, serde_json::Error> =
                        serde_json::from_str(ie.data.as_str());
                    if subs_res.is_ok() {
                        let subs = subs_res.unwrap().clone();
                        match task {
                            IndraTask::DingDong(st) => {
                                let old_subs = st.subs.clone();
                                for sub in subs {
                                    let index = st.subs.iter().position(|x| *x == sub);
                                    if index.is_some() {
                                        st.subs.remove(index.unwrap());
                                    }
                                }
                                debug!("UN-SUBS: {}: {:?} -> {:?}", name, old_subs, st.subs);
                            }
                            IndraTask::Mqtt(st) => {
                                let old_subs = st.subs.clone();
                                for sub in subs {
                                    let index = st.subs.iter().position(|x| *x == sub);
                                    if index.is_some() {
                                        st.subs.remove(index.unwrap());
                                    }
                                }
                                debug!("UN-SUBS: {}: {:?} -> {:?}", name, old_subs, st.subs);
                            }
                            IndraTask::Web(st) => {
                                let old_subs = st.subs.clone();
                                for sub in subs {
                                    let index = st.subs.iter().position(|x| *x == sub);
                                    if index.is_some() {
                                        st.subs.remove(index.unwrap());
                                    }
                                }
                                debug!("UN-SUBS: {}: {:?} -> {:?}", name, old_subs, st.subs)
                            }
                            IndraTask::SQLx(st) => {
                                let old_subs = st.subs.clone();
                                for sub in subs {
                                    let index = st.subs.iter().position(|x| *x == sub);
                                    if index.is_some() {
                                        st.subs.remove(index.unwrap());
                                    }
                                }
                                debug!("UN-SUBS: {}: {:?} -> {:?}", name, old_subs, st.subs)
                            }
                            IndraTask::Ws(st) => {
                                let old_subs = st.subs.clone();
                                for sub in subs {
                                    let index = st.subs.iter().position(|x| *x == sub);
                                    if index.is_some() {
                                        st.subs.remove(index.unwrap());
                                    }
                                }
                                debug!("UN-SUBS: {}: {:?} -> {:?}", name, old_subs, st.subs)
                            }
                            IndraTask::Signal(st) => {
                                let old_subs = st.subs.clone();
                                for sub in subs {
                                    let index = st.subs.iter().position(|x| *x == sub);
                                    if index.is_some() {
                                        st.subs.remove(index.unwrap());
                                    }
                                }
                                debug!("UN-SUBS: {}: {:?} -> {:?}", name, old_subs, st.subs)
                            }
                            IndraTask::Tasker(st) => {
                                let old_subs = st.subs.clone();
                                for sub in subs {
                                    let index = st.subs.iter().position(|x| *x == sub);
                                    if index.is_some() {
                                        st.subs.remove(index.unwrap());
                                    }
                                }
                                debug!("UN-SUBS: {}: {:?} -> {:?}", name, old_subs, st.subs)
                            }
                            IndraTask::Llm(st) => {
                                let old_subs = st.subs.clone();
                                for sub in subs {
                                    let index = st.subs.iter().position(|x| *x == sub);
                                    if index.is_some() {
                                        st.subs.remove(index.unwrap());
                                    }
                                }
                                debug!("UN-SUBS: {}: {:?} -> {:?}", name, old_subs, st.subs)
                            }
                        }
                    } else {
                        error!("{}: {} unsubs: {:?}", ie.from_id, name, subs_res);
                    }
                    continue;
                } else {
                    debug!("{}, {} no match", ie.from_id, name_subs);
                }
            }

            if ie.from_id == "$trx/echo" {
                continue; // Echo is only sent to the originating task
            }

            if IndraEvent::check_route(&ie.domain, &name, &subs, None) || ie.domain == "$cmd/quit" {
                let mut sdata = ie.data.to_string();
                if sdata.len() > 16 {
                    sdata.truncate(16);
                    sdata += "...";
                }
                info!(
                    "ROUTE: from: {} to: {} task {} [{}:{}]",
                    ie.from_id, ie.domain, name, sdata, ie.data_type,
                );
                let _ = acs.send(ie.clone()).await;
            }
        }
        if !from_ident {
            error!(
                "ERROR: invalid from_instance in {:#?}, could not identify originating task!",
                ie
            );
        }
        if quit_cmd_received {
            warn!("Router: QUIT command received, exiting.");
            break;
        }
    }
}

const CHECK_INTERVAL: Duration = Duration::from_secs(3);
const MAX_CHECK_DURATION: Duration = Duration::from_secs(60);

fn check_internet_connection() -> bool {
    let servers = vec![
        "https://www.google.com",
        "https://www.cloudflare.com",
        "https://aws.amazon.com",
        "https://azure.microsoft.com",
    ];

    let mut timed_out = false;
    let start_time = Instant::now();
    while start_time.elapsed() < MAX_CHECK_DURATION {
        for server in &servers {
            match get(*server) {
                Ok(response) => {
                    if response.status().is_success() {
                        if timed_out {
                            warn!("Internet connection is now available! Continuing normal operation.");
                        }
                        return true; // At least one server is accessible
                    }
                }
                Err(_) => continue, // Try the next server
            }
        }
        if !timed_out {
            warn!("No internet connection available, halting operation while retrying connection to internet...",);
        }
        timed_out = true;
        thread::sleep(CHECK_INTERVAL);
    }
    warn!("No internet connection available, giving up.");

    false // None of the servers were accessible within the maximum check duration
}

fn main() {
    //let indra_config: IndraConfig = IndraConfig::new();

    let (imc, indra_config, state_msg) = IndraConfig::new();
    if !imc.data_directory.exists() {
        println!(
            "Data directory {} does not exist, please create it, or change entry in {}.",
            imc.data_directory.to_string_lossy(),
            imc.config_file.to_string_lossy()
        );
        std::process::exit(1);
    }
    let log_dir = imc.data_directory.join("log");
    if !log_dir.exists() {
        // create dir
        match fs::create_dir(&log_dir) {
            Ok(_) => {}
            Err(e) => {
                error!("Failed to create log directory: {}", e);
                std::process::exit(1);
            }
        }
    }
    let lf = LevelFilter::from_str(&imc.default_term_log).unwrap_or(LevelFilter::Info);
    Logger::try_with_str(imc.default_file_log.as_str())
        .unwrap_or_else(|_| panic!("Failed to initialize term logger {}", imc.default_term_log))
        .format_for_files(detailed_format)
        .format_for_stdout(colored_detailed_format)
        .log_to_file(FileSpec::default().directory(log_dir))
        .write_mode(WriteMode::BufferDontFlush)
        .rotate(
            // If the program runs long enough,
            Criterion::Age(Age::Day), // - create a new file every day
            Naming::Timestamps,       // - let the rotated files have a timestamp in their name
            Cleanup::KeepLogFiles(7), // - keep at most 7 log files
        )
        .duplicate_to_stdout(Duplicate::from(lf))
        .start()
        .unwrap();

    if !state_msg.is_empty() {
        warn!("{}", state_msg);
    }
    if check_internet_connection() {
        debug!("Internet connection is available.");
    } else {
        error!("No internet connection available!");
    }

    let mut tsk: Vec<IndraTask> = vec![];

    if indra_config.mqtt.is_some() {
        for mq in indra_config.mqtt.clone().unwrap() {
            let m = Mqtt::new(mq.clone());
            tsk.push(IndraTask::Mqtt(m.clone()));
        }
    }
    if indra_config.ding_dong.is_some() {
        for dd in indra_config.ding_dong.clone().unwrap() {
            let d = DingDong::new(dd.clone());
            tsk.push(IndraTask::DingDong(d.clone()));
        }
    }
    if indra_config.web.is_some() {
        for rs in indra_config.web.clone().unwrap() {
            let r = Web::new(rs.clone());
            tsk.push(IndraTask::Web(r.clone()));
        }
    }
    if indra_config.sqlx.is_some() {
        for sq in indra_config.sqlx.clone().unwrap() {
            let s = SQLx::new(sq.clone());
            tsk.push(IndraTask::SQLx(s.clone()));
        }
    }
    if indra_config.ws.is_some() {
        for rs in indra_config.ws.clone().unwrap() {
            let w = Ws::new(rs.clone());
            tsk.push(IndraTask::Ws(w.clone()));
        }
    }
    if indra_config.signal.is_some() {
        for si in indra_config.signal.clone().unwrap() {
            let si: Signal = Signal::new(si.clone());
            tsk.push(IndraTask::Signal(si.clone()));
        }
    }
    if indra_config.tasker.is_some() {
        for ta in indra_config.tasker.clone().unwrap() {
            let ta: Tasker = Tasker::new(ta.clone());
            tsk.push(IndraTask::Tasker(ta.clone()));
        }
    }
    if indra_config.llm.is_some() {
        // Technically, this is redundant, but once another task is added, this will be needed.
        #[allow(clippy::redundant_clone)]
        for ll in indra_config.llm.clone().unwrap() {
            let ll: Llm = Llm::new(ll.clone());
            tsk.push(IndraTask::Llm(ll.clone()));
        }
    }

    let (sender, receiver) = async_channel::unbounded::<IndraEvent>();
    let mut join_handles: Vec<task::JoinHandle<()>> = vec![];
    task::block_on(async {
        let router_task = task::spawn(router(tsk.clone(), receiver));
        join_handles.push(router_task);
        for task in tsk {
            match task {
                IndraTask::DingDong(st) => {
                    join_handles.push(task::spawn(st.clone().async_sender(sender.clone())));
                    join_handles.push(task::spawn(st.clone().async_receiver(sender.clone())));
                }
                IndraTask::Mqtt(st) => {
                    join_handles.push(task::spawn(st.clone().async_sender(sender.clone())));
                    join_handles.push(task::spawn(st.clone().async_receiver(sender.clone())));
                }
                IndraTask::Web(st) => {
                    join_handles.push(task::spawn(st.clone().async_sender(sender.clone())));
                    join_handles.push(task::spawn(st.clone().async_receiver(sender.clone())));
                }
                IndraTask::SQLx(st) => {
                    join_handles.push(task::spawn(st.clone().async_sender(sender.clone())));
                    join_handles.push(task::spawn(st.clone().async_receiver(sender.clone())));
                }
                IndraTask::Ws(st) => {
                    join_handles.push(task::spawn(st.clone().async_sender(sender.clone())));
                    join_handles.push(task::spawn(st.clone().async_receiver(sender.clone())));
                }
                IndraTask::Signal(st) => {
                    join_handles.push(task::spawn(st.clone().async_sender(sender.clone())));
                    join_handles.push(task::spawn(st.clone().async_receiver(sender.clone())));
                }
                IndraTask::Tasker(ta) => {
                    join_handles.push(task::spawn(ta.clone().async_sender(sender.clone())));
                    join_handles.push(task::spawn(ta.clone().async_receiver(sender.clone())));
                }
                IndraTask::Llm(ll) => {
                    join_handles.push(task::spawn(ll.clone().async_sender(sender.clone())));
                    join_handles.push(task::spawn(ll.clone().async_receiver(sender.clone())));
                }
            }
        }
        for handle in join_handles {
            handle.await;
        }
    });
}
