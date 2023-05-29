// WARNING: async fn in trait is experimental, requires nightly, but nightly beyond 2023-05-01 will
// break llm's dependencies, so for now we lock to nightly-2021-05-01, using:
// rustup override set nightly-2023-05-01-x86_64-unknown-linux-gnu

#![allow(incomplete_features)]
#![feature(async_fn_in_trait)]
#![feature(async_closure)]
// avoid boxing: (exp!)
#![feature(type_alias_impl_trait)]

use env_logger::Env;
use log::{debug, error, info, warn};

use async_channel;
use async_std::task;

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
use in_async_llm::LLM;

#[derive(Clone)]
enum IndraTask {
    Mqtt(Mqtt),
    Web(Web),
    DingDong(DingDong),
    SQLx(SQLx),
    Ws(Ws),
    Signal(Signal),
    Tasker(Tasker),
    LLM(LLM),
}

trait AsyncTaskSender {
    async fn async_sender(self, sender: async_channel::Sender<IndraEvent>);
}

trait AsyncTaskReceiver {
    async fn async_receiver(self, sender: async_channel::Sender<IndraEvent>);
}

async fn router(tsk: Vec<IndraTask>, receiver: async_channel::Receiver<IndraEvent>) {
    let mut quit_cmd_received: bool = false;
    loop {
        let msg = receiver.recv().await;
        let ie = msg.unwrap();
        let mut from_ident = false;
        if ie.from_id == "" {
            error!(
                "ERROR: ignoring {:#?}, from_instance is not set, can't avoid recursion.",
                ie
            );
        }
        debug!("IE-Event: {} {} {}", ie.time_jd_start, ie.domain, ie.data);
        for task in &tsk {
            let ot: Vec<String>;
            let ob: Vec<String>;
            let act: bool;
            let acs: async_channel::Sender<IndraEvent>;
            let name: String;
            match task {
                IndraTask::DingDong(st) => {
                    ot = st.config.clone().out_topics;
                    ob = st.config.clone().out_blocks;
                    act = st.config.clone().active;
                    acs = st.sender.clone();
                    name = st.config.clone().name;
                }
                IndraTask::Mqtt(st) => {
                    ot = st.config.clone().out_topics;
                    ob = st.config.clone().out_blocks;
                    act = st.config.clone().active;
                    acs = st.sender.clone();
                    name = st.config.clone().name;
                }
                IndraTask::Web(st) => {
                    ot = st.config.clone().out_topics;
                    ob = st.config.clone().out_blocks;
                    act = st.config.clone().active;
                    acs = st.sender.clone();
                    name = st.config.clone().name;
                }
                IndraTask::SQLx(st) => {
                    ot = st.config.clone().out_topics;
                    ob = st.config.clone().out_blocks;
                    act = st.config.clone().active;
                    acs = st.sender.clone();
                    name = st.config.clone().name;
                }
                IndraTask::Ws(st) => {
                    ot = st.config.clone().out_topics;
                    ob = st.config.clone().out_blocks;
                    act = st.config.clone().active;
                    acs = st.sender.clone();
                    name = st.config.clone().name;
                }
                IndraTask::Signal(st) => {
                    ot = st.config.clone().out_topics;
                    ob = st.config.clone().out_blocks;
                    act = st.config.clone().active;
                    acs = st.sender.clone();
                    name = st.config.clone().name;
                }
                IndraTask::Tasker(st) => {
                    ot = st.config.clone().out_topics;
                    ob = st.config.clone().out_blocks;
                    act = st.config.clone().active;
                    acs = st.sender.clone();
                    name = st.config.clone().name;
                }
                IndraTask::LLM(st) => {
                    ot = st.config.clone().out_topics;
                    ob = st.config.clone().out_blocks;
                    act = st.config.clone().active;
                    acs = st.sender.clone();
                    name = st.config.clone().name;
                }
            }
            if act == false {
                continue;
            }
            let name_subs = name.clone() + "/#";
            if IndraEvent::mqcmp(&ie.from_id, &name_subs) || (&ie.from_id == &name) {
                if ie.domain != "$cmd/quit" {
                    debug!(
                        "NOT sending {} to {}, recursion avoidance.",
                        ie.from_id, name
                    );
                    from_ident = true;
                    continue;
                } else {
                    quit_cmd_received = true;
                }
                from_ident = true;
            } else {
                debug!("{}, {} no match", ie.from_id, name_subs);
            }
            if IndraEvent::check_route(&ie.domain, &name, &ot, &ob) || ie.domain == "$cmd/quit" {
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
        if from_ident == false {
            error!(
                "ERROR: invalid from_instance in {:#?}, could not identify originating task!",
                ie
            );
        }
        if quit_cmd_received == true {
            warn!("Router: QUIT command received, exiting.");
            break;
        }
    }
}

fn main() {
    //let indra_config: IndraConfig = IndraConfig::new();

    let indra_config = IndraConfig::new();

    env_logger::Builder::from_env(Env::default().default_filter_or("indrajala=info"))
        .format_timestamp(Some(env_logger::TimestampPrecision::Millis))
        .init();

    let mut tsk: Vec<IndraTask> = vec![];

    if !indra_config.mqtt.is_none() {
        for mq in indra_config.mqtt.clone().unwrap() {
            let m = Mqtt::new(mq.clone());
            tsk.push(IndraTask::Mqtt(m.clone()));
        }
    }
    if !indra_config.ding_dong.is_none() {
        for dd in indra_config.ding_dong.clone().unwrap() {
            let d = DingDong::new(dd.clone());
            tsk.push(IndraTask::DingDong(d.clone()));
        }
    }
    if !indra_config.web.is_none() {
        for rs in indra_config.web.clone().unwrap() {
            let r = Web::new(rs.clone());
            tsk.push(IndraTask::Web(r.clone()));
        }
    }
    if !indra_config.sqlx.is_none() {
        for sq in indra_config.sqlx.clone().unwrap() {
            let s = SQLx::new(sq.clone());
            tsk.push(IndraTask::SQLx(s.clone()));
        }
    }
    if !indra_config.ws.is_none() {
        for rs in indra_config.ws.clone().unwrap() {
            let w = Ws::new(rs.clone());
            tsk.push(IndraTask::Ws(w.clone()));
        }
    }
    if !indra_config.signal.is_none() {
        for si in indra_config.signal.clone().unwrap() {
            let si: Signal = Signal::new(si.clone());
            tsk.push(IndraTask::Signal(si.clone()));
        }
    }
    if !indra_config.tasker.is_none() {
        for ta in indra_config.tasker.clone().unwrap() {
            let ta: Tasker = Tasker::new(ta.clone());
            tsk.push(IndraTask::Tasker(ta.clone()));
        }
    }
    if !indra_config.llm.is_none() {
        for ll in indra_config.llm.clone().unwrap() {
            let ll: LLM = LLM::new(ll.clone());
            tsk.push(IndraTask::LLM(ll.clone()));
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
                IndraTask::LLM(ll) => {
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
