#![feature(async_fn_in_trait)]

use async_channel;
use async_std::task;

mod indra_event;
use indra_event::IndraEvent;
mod indra_config;
use indra_config::IndraTaskConfig;

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

trait AsyncTaskSender {
    async fn async_receiver(self, sender: async_channel::Sender<IndraEvent>);
}
trait AsyncTaskReceiver {
    async fn async_sender(self);
}

async fn router(tsk: Vec<IndraTask>, dd: DingDong, receiver: async_channel::Receiver<IndraEvent>) {
    loop {
        let msg = receiver.recv().await;
        let ie = msg.unwrap();
        println!("{} {} {}", ie.time_jd_start, ie.domain, ie.data);
        for task in &tsk {
            if task.active == false {
                continue;
            }
            for topic in &task.out_topics {
                println!("router: {} {} {}", task.name, topic, ie.domain);
                if IndraEvent::mqcmp(&ie.domain, &topic) {
                    let mut blocked = false;
                    /* for out_block in &dd.config.out_blocks {
                        if IndraEvent::mqcmp(&ie.domain, &out_block) {
                            println!("router: {} {} {} blocked", task.name, topic, ie.domain);
                            blocked = true;
                        }
                    }
                    */
                    if blocked {
                        continue;
                    }
                    println!("sending route to {}, {}", task.name, ie.domain);
                    let _ = task.out_channel.send(ie.clone()).await;
                }
            }
        }
    }
}

fn main() {
    //let indra_config: IndraConfig = IndraConfig::new();

    IndraTaskConfig::read_tasks();
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
}
