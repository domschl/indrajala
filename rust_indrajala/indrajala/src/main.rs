//use std::time::Duration;
use async_channel;
use async_std::task;
use std::env;
use std::path::Path;

mod indra_event;
use indra_event::IndraEvent;
mod indra_config;
use indra_config::IndraConfig;

mod in_async_mqtt;
use in_async_mqtt::mq;
mod ding_dong;
use ding_dong::ding_dong;

async fn router(receiver: async_channel::Receiver<IndraEvent>) {
    loop {
        let msg = receiver.recv().await;
        let ie = msg.unwrap();
        println!("{} {} {}", ie.time_start, ie.domain, ie.data);
    }
}

fn main() {
    // read command line arguments
    let args: Vec<String> = env::args().collect();
    // Check if at least one argument is passed
    if args.len() < 2 {
        println!("Usage: {} <config_file>", args[0]);
        std::process::exit(1);
    }
    // Check if the file exists
    if !Path::new(&args[1]).exists() {
        println!("File {} does not exist, it should be a TOML file", args[1]);
        std::process::exit(1);
    }

    let config = IndraConfig::new(&args[1]);

    let (sender, receiver) = async_channel::unbounded::<IndraEvent>();

    let server = config.get_value("in_async_mqtt", "broker");
    let server_uri = format!("tcp://{}:1883", server);

    // Start both tasks: mq and router:
    task::block_on(async {
        let mq_task = task::spawn(mq(server_uri, sender.clone()));
        let router_task = task::spawn(router(receiver));
        let ding_dong_task = task::spawn(ding_dong(sender.clone()));
        mq_task.await;
        router_task.await;
        ding_dong_task.await;
    });
}
