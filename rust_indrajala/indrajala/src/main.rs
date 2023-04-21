#![allow(incomplete_features)]
#![feature(async_fn_in_trait)]

use async_channel;
use async_std::task;

mod indra_event;
use indra_event::IndraEvent;
mod indra_config;
use indra_config::IndraConfig;

mod ding_dong;
use ding_dong::DingDong;
mod in_async_mqtt;
use in_async_mqtt::Mqtt;
mod in_async_rest;
use in_async_rest::Rest;
mod in_async_sqlx;
use in_async_sqlx::SQLx;

#[derive(Clone)]
enum IndraTask {
    Mqtt(Mqtt),
    Rest(Rest),
    DingDong(DingDong),
    SQLx(SQLx),
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
        println!("{} {} {}", ie.time_jd_start, ie.domain, ie.data);
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
                IndraTask::Rest(st) => {
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
            }

            if act == false {
                continue;
            }
            for topic in &ot {
                println!("router: {} {} {}", name, topic, ie.domain);
                if IndraEvent::mqcmp(&ie.domain, &topic) {
                    let mut blocked = false;
                    for out_block in &ob {
                        if IndraEvent::mqcmp(&ie.domain, &out_block) {
                            println!("router: {} {} {} blocked", name, topic, ie.domain);
                            blocked = true;
                        }
                    }

                    if blocked {
                        continue;
                    }
                    println!("sending route {} to {}", name, ie.domain);
                    let _ = acs.send(ie.clone()).await;
                }
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
    if !indra_config.rest.is_none() {
        for rs in indra_config.rest.clone().unwrap() {
            let r = Rest::new(rs.clone());
            tsk.push(IndraTask::Rest(r.clone()));
        }
    }
    if !indra_config.sqlx.is_none() {
        for sq in indra_config.sqlx.clone().unwrap() {
            let s = SQLx::new(sq.clone());
            tsk.push(IndraTask::SQLx(s.clone()));
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
                IndraTask::Rest(st) => {
                    join_handles.push(task::spawn(st.clone().async_receiver(sender.clone())));
                    join_handles.push(task::spawn(st.clone().async_sender()));
                }
                IndraTask::SQLx(st) => {
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
