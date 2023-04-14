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

fn mqcmp(pub_str: &str, sub: &str) -> bool {
    for c in ["+", "#"] {
        if pub_str.contains(c) {
            println!("Illegal char '{}' in pub in mqcmp!", c);
            return false;
        }
    }
    let mut inds = 0;
    let mut wcs = false;
    for (_indp, c) in pub_str.chars().enumerate() {
        if wcs {
            if c == '/' {
                inds += 1;
                wcs = false;
            }
            continue;
        }
        if inds >= sub.len() {
            return false;
        }
        if c == sub.chars().nth(inds).unwrap() {
            inds += 1;
            continue;
        }
        if sub.chars().nth(inds).unwrap() == '#' {
            return true;
        }
        if sub.chars().nth(inds).unwrap() == '+' {
            wcs = true;
            inds += 1;
            continue;
        }
        if c != sub.chars().nth(inds).unwrap() {
            return false;
        }
    }
    if sub[inds..].len() == 0 {
        return true;
    }
    if sub[inds..].len() == 1 {
        if sub.chars().nth(inds).unwrap() == '+' || sub.chars().nth(inds).unwrap() == '#' {
            return true;
        }
    }
    false
}

async fn router(tsk: Vec<IndraTask>, dd: DingDong, receiver: async_channel::Receiver<IndraEvent>) {
    loop {
        let msg = receiver.recv().await;
        let ie = msg.unwrap();
        for task in &tsk {
            if task.active == false {
                continue;
            }
            for topic in &task.out_topics {
                println!("router: {} {} {}", task.name, topic, ie.domain);
                if mqcmp(&ie.domain, &topic) {
                    let mut blocked = false;
                    for out_block in &dd.config.out_blocks {
                        if mqcmp(&ie.domain, &out_block) {
                            println!("router: {} {} {} blocked", task.name, topic, ie.domain);
                            blocked = true;
                        }
                    }
                    if blocked {
                        continue;
                    }
                    let _ = task.out_channel.send(ie.clone()).await;
                }
            }
        }
        //println!("{} {} {}", ie.time_start, ie.domain, ie.data);
    }
}

fn main() {
    let indra_config: IndraConfig = IndraConfig::new();
    let (sender, receiver) = async_channel::unbounded::<IndraEvent>();
    let mut tsk: Vec<IndraTask> = vec![];

    // DingDong
    let d = DingDong::new(indra_config.dingdong.clone());
    tsk.push(d.clone().task.clone());

    // Mqtt
    let m = Mqtt::new(indra_config.mqtt.clone());
    tsk.push(m.clone().task.clone());

    task::block_on(async {
        let router_task = task::spawn(router(tsk.clone(), d.clone(), receiver));

        let ding_dong_task = task::spawn(d.clone().async_receiver(sender.clone()));
        let ding_dong_task_s = task::spawn(d.clone().async_sender());

        let mqtt_task = task::spawn(m.clone().async_receiver(sender.clone()));
        let mqtt_task_s = task::spawn(m.clone().async_sender());

        router_task.await;

        ding_dong_task.await;
        ding_dong_task_s.await;

        mqtt_task.await;
        mqtt_task_s.await;
    });
}
