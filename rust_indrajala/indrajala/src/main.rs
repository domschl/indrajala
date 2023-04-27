#![allow(incomplete_features)]
#![feature(async_fn_in_trait)]

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
use in_async_ws::{init_websocket_server, Ws};

#[derive(Clone)]
enum IndraTask {
    Mqtt(Mqtt),
    Web(Web),
    DingDong(DingDong),
    SQLx(SQLx),
    Ws(Ws),
}

trait AsyncTaskSender {
    async fn async_receiver(self, sender: async_channel::Sender<IndraEvent>);
}
trait AsyncTaskReceiver {
    async fn async_sender(self);
}

async fn router(tsk: Vec<IndraTask>, receiver: async_channel::Receiver<IndraEvent>) {
    loop {
        let msg = receiver.recv().await;
        let ie = msg.unwrap();
        //println!("{} {} {}", ie.time_jd_start, ie.domain, ie.data);
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
            }
            if act == false {
                continue;
            }
            if IndraEvent::check_route(&ie.domain, &name, &ot, &ob) {
                //println!("sending route {} to {}", ie.domain, name);
                let _ = acs.send(ie.clone()).await;
            }
        }
    }
}

fn main() {
    //let indra_config: IndraConfig = IndraConfig::new();

    let indra_config = IndraConfig::new();

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

    let (sender, receiver) = async_channel::unbounded::<IndraEvent>();
    let mut join_handles: Vec<task::JoinHandle<()>> = vec![];
    task::block_on(async {
        let router_task = task::spawn(router(tsk.clone(), receiver));
        join_handles.push(router_task);
        for task in tsk {
            match task {
                IndraTask::DingDong(st) => {
                    join_handles.push(task::spawn(st.clone().async_receiver(sender.clone())));
                    join_handles.push(task::spawn(st.clone().async_sender()));
                }
                IndraTask::Mqtt(st) => {
                    join_handles.push(task::spawn(st.clone().async_receiver(sender.clone())));
                    join_handles.push(task::spawn(st.clone().async_sender()));
                }
                IndraTask::Web(st) => {
                    join_handles.push(task::spawn(st.clone().async_receiver(sender.clone())));
                    join_handles.push(task::spawn(st.clone().async_sender()));
                }
                IndraTask::SQLx(st) => {
                    join_handles.push(task::spawn(st.clone().async_receiver(sender.clone())));
                    join_handles.push(task::spawn(st.clone().async_sender()));
                }
                IndraTask::Ws(st) => {
                    join_handles.push(task::spawn(init_websocket_server(
                        st.clone().connections,
                        st.clone().config.address,
                        st.clone().sender.clone(),
                    )));
                    join_handles.push(task::spawn(st.clone().async_receiver(sender.clone())));
                    join_handles.push(task::spawn(st.clone().async_sender()));
                }
            }
        }
        for handle in join_handles {
            handle.await;
        }
    });
}
