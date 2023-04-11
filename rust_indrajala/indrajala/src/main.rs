//use std::time::Duration;
use async_std::task;
use std::env;
use std::fs;
use std::path::Path;
use toml::Value;

mod in_async_mqtt;
use in_async_mqtt::mq;

fn read_config(toml_file: &str) -> String {
    let toml_str = fs::read_to_string(toml_file).unwrap();
    let value = toml_str.parse::<Value>().unwrap();
    let server = value["in_async_mqtt"]["broker"].as_str().unwrap();
    // convert server hostname to uri of type tpc://hostname:1883
    let server_uri = format!("tcp://{}:1883", server);
    return server_uri;
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

    let broker = read_config(&args[1]);
    task::block_on(mq(broker));
}
