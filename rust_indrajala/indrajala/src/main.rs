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
pub struct IndraTask {
    name: String,
    active: bool,
    out_topics: Vec<String>,
    out_channel: async_channel::Sender<IndraEvent>,
}

#[derive(Clone)]
enum IndraSubTask {
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

async fn router(tsk: Vec<IndraSubTask>, receiver: async_channel::Receiver<IndraEvent>) {
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
                IndraSubTask::DingDong(st) => {
                    ot = st.config.clone().out_topics;
                    ob = st.config.clone().out_blocks;
                    act = st.config.clone().active;
                    acs = st.task.clone().out_channel;
                    name = st.config.clone().name;
                }
                IndraSubTask::Mqtt(st) => {
                    ot = st.config.clone().out_topics;
                    ob = st.config.clone().out_blocks;
                    act = st.config.clone().active;
                    acs = st.task.clone().out_channel;
                    name = st.config.clone().name;
                }
                IndraSubTask::Rest(st) => {
                    ot = st.config.clone().out_topics;
                    ob = st.config.clone().out_blocks;
                    act = st.config.clone().active;
                    acs = st.task.clone().out_channel;
                    name = st.config.clone().name;
                }
                IndraSubTask::SQLx(st) => {
                    ot = st.config.clone().out_topics;
                    ob = st.config.clone().out_blocks;
                    act = st.config.clone().active;
                    acs = st.task.clone().out_channel;
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

    let mut tsk: Vec<IndraSubTask> = vec![];

    if !indra_config.MQTT.is_none() {
        for mq in indra_config.MQTT.clone().unwrap() {
            let m = Mqtt::new(mq.clone());
            tsk.push(IndraSubTask::Mqtt(m.clone()));
        }
    }
    if !indra_config.DingDong.is_none() {
        for dd in indra_config.DingDong.clone().unwrap() {
            let d = DingDong::new(dd.clone());
            tsk.push(IndraSubTask::DingDong(d.clone()));
        }
    }
    if !indra_config.Rest.is_none() {
        for rs in indra_config.Rest.clone().unwrap() {
            let r = Rest::new(rs.clone());
            tsk.push(IndraSubTask::Rest(r.clone()));
        }
    }
    if !indra_config.SQLx.is_none() {
        for sq in indra_config.SQLx.clone().unwrap() {
            let s = SQLx::new(sq.clone());
            tsk.push(IndraSubTask::SQLx(s.clone()));
        }
    }

    let (sender, receiver) = async_channel::unbounded::<IndraEvent>();
    let mut join_handles: Vec<task::JoinHandle<()>> = vec![];
    task::block_on(async {
        let router_task = task::spawn(router(tsk.clone(), receiver));
        join_handles.push(router_task);
        for task in tsk {
            match task {
                IndraSubTask::DingDong(st) => {
                    join_handles.push(task::spawn(st.clone().async_receiver(sender.clone())));
                }
                IndraSubTask::Mqtt(st) => {
                    join_handles.push(task::spawn(st.clone().async_receiver(sender.clone())));
                }
                IndraSubTask::Rest(st) => {
                    join_handles.push(task::spawn(st.clone().async_receiver(sender.clone())));
                }
                IndraSubTask::SQLx(st) => {
                    join_handles.push(task::spawn(st.clone().async_receiver(sender.clone())));
                }
            }
        }
        for handle in join_handles {
            handle.await;
        }
    });
}
