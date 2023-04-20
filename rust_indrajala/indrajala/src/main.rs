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
            match task {
                IndraSubTask::DingDong(st) => {
                    ot = st.config.clone().out_topics;
                    ob = st.config.clone().out_blocks;
                    act = st.config.clone().active;
                    acs = st.task.clone().out_channel;
                }
                IndraSubTask::Mqtt(st) => {
                    ot = st.config.clone().out_topics;
                    ob = st.config.clone().out_blocks;
                    act = st.config.clone().active;
                    acs = st.task.clone().out_channel;
                }
                IndraSubTask::Rest(st) => {
                    ot = st.config.clone().out_topics;
                    ob = st.config.clone().out_blocks;
                    act = st.config.clone().active;
                    acs = st.task.clone().out_channel;
                }
                IndraSubTask::SQLx(st) => {
                    ot = st.config.clone().out_topics;
                    ob = st.config.clone().out_blocks;
                    act = st.config.clone().active;
                    acs = st.task.clone().out_channel;
                }
            }

            if act == false {
                continue;
            }
            for topic in &ot {
                println!("router: {} {}", topic, ie.domain);
                if IndraEvent::mqcmp(&ie.domain, &topic) {
                    let mut blocked = false;
                    for out_block in &ob {
                        if IndraEvent::mqcmp(&ie.domain, &out_block) {
                            println!("router: {} {} blocked", topic, ie.domain);
                            blocked = true;
                        }
                    }

                    if blocked {
                        continue;
                    }
                    println!("sending route to {}", ie.domain);
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
/*

let (sender, receiver) = async_channel::unbounded::<IndraEvent>();
let mut tsk: Vec<IndraTask> = vec![];

// DingDong
let d = DingDong::new(indra_config.dingdong.clone());
tsk.push(d.clone().task.clone());

// Mqtt
let m = Mqtt::new(indra_config.mqtt.clone());
tsk.push(m.clone().task.clone());

let r: Rest = Rest::new(indra_config.rest.clone());
tsk.push(r.clone().task.clone());

let s: SQLx = SQLx::new(indra_config.sqlx.clone());
//let mut ret = false;
/* task::block_on(async {
    ret = s.async_init().await;
});
*/
/*
match ret {
    Some(true) => {
        println!("SQLx init success!");
        s.config.active = true;
    }
    Some(false) => {
        println!("SQLx init failed!");
        s.config.active = false;
    }
    None => {
        println!("SQLx init failed!");
        s.config.active = false;
    }
}
 */
tsk.push(s.task.clone());

task::block_on(async {
    let router_task = task::spawn(router(tsk.clone(), d.clone(), receiver));

    let ding_dong_task = task::spawn(d.clone().async_receiver(sender.clone()));
    let ding_dong_task_s = task::spawn(d.clone().async_sender());

    let mqtt_task = task::spawn(m.clone().async_receiver(sender.clone()));
    let mqtt_task_s = task::spawn(m.clone().async_sender());

    let rest_task = task::spawn(r.clone().async_receiver(sender.clone()));
    let rest_task_s = task::spawn(r.clone().async_sender());

    let sqlx_task = task::spawn(s.clone().async_receiver(sender.clone()));
    let sqlx_task_s = task::spawn(s.clone().async_sender());

    router_task.await;

    ding_dong_task.await;
    ding_dong_task_s.await;

    mqtt_task.await;
    mqtt_task_s.await;

    rest_task.await;
    rest_task_s.await;

    sqlx_task.await;
    sqlx_task_s.await;
});
 */
//}
