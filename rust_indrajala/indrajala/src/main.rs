#![feature(async_fn_in_trait)]

//use std::time::Duration;
use async_channel;
use async_std::task;
//use std::future::Future;

mod indra_event;
use indra_event::IndraEvent;
mod indra_config;
use indra_config::IndraConfig;

mod in_async_mqtt;
use in_async_mqtt::{mq, mq_send};
mod ding_dong;
use ding_dong::DingDong;

#[derive(Clone)]
struct IndraTask {
    name: String,
    active: bool,
    out_topics: Vec<String>,
    out_channel: async_channel::Sender<IndraEvent>,
    in_channel: async_channel::Receiver<IndraEvent>,
}

trait AsyncTaskSender {
    async fn async_receiver(self, sender: async_channel::Sender<IndraEvent>);
}
trait AsyncTaskReceiver {
    async fn async_sender(self, receiver: &IndraEvent);
}

trait TaskInit {
    fn init(self, config: IndraConfig, task: IndraTask) -> u32;
}

trait AsyncTaskInit {
    async fn async_init(self, config: IndraConfig, task: IndraTask) -> u32;
}

/*x
where
    S: Future,
    T: Future,
{
    receiver: fn(mqtt_config: IndraConfig, sender: async_channel::Sender<IndraEvent>) -> S,
    sender: fn(IndraEvent) -> T,
    out_topics: Vec<String>,
}
*/
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
            for topic in &task.out_topics {
                if mqcmp(&ie.domain, &topic) {}
            }
        }

        println!("{} {} {}", ie.time_start, ie.domain, ie.data);
    }
}
/*
impl<S, T> TaskEntry<S, T>
where
    S: Future,
    T: Future,
{
    fn new(
        receiver: fn(mqtt_config: IndraConfig, sender: async_channel::Sender<IndraEvent>) -> S,
        sender: fn(IndraEvent) -> T,
        out_topics: Vec<String>,
    ) -> Self {
        Self {
            receiver,
            sender,
            out_topics,
        }
    }
}
*/

fn main() {
    let indra_config: IndraConfig = IndraConfig::new();

    let (sender, receiver) = async_channel::unbounded::<IndraEvent>();

    let mut tsk: Vec<IndraTask> = vec![];

    let d = DingDong {
        topic: indra_config.dingdong.topic.clone(),
        message: indra_config.dingdong.message.clone(),
        timer: indra_config.dingdong.timer,
    };

    let (dd_sender, dd_receiver) = async_channel::unbounded::<IndraEvent>();

    let t1 = IndraTask {
        name: "DingDong".to_string(),
        active: true,
        out_topics: vec![indra_config.dingdong.topic.clone()],
        out_channel: dd_sender.clone(),
        in_channel: dd_receiver.clone(),
    };
    tsk.push(t1.clone());
    //d.init(indra_config.clone());

    // Start both tasks: mq and router:
    task::block_on(async {
        let mq_task = task::spawn(mq(indra_config.clone(), sender.clone()));
        let router_task = task::spawn(router(tsk.clone(), d.clone(), receiver));
        let ding_dong_task = task::spawn(d.async_receiver(sender.clone()));
        mq_task.await;
        router_task.await;
        ding_dong_task.await;
    });
}
