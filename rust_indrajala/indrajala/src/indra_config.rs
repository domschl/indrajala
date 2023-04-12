use serde::Deserialize;
use std::env;
use std::fs;
use std::path::Path;

#[derive(Deserialize)]
pub struct IndraConfig {
    pub mqtt: MqttConfig,
    pub dingdong: DingDongConfig,
}

#[derive(Deserialize)]
pub struct MqttConfig {
    pub host: String,
    pub port: u16,
    pub username: String,
    pub password: String,
    pub client_id: String,
    pub topics: Vec<String>,
}

#[derive(Deserialize)]
pub struct DingDongConfig {
    pub timer: u32,
    pub topic: String,
    pub message: String,
}

impl IndraConfig {
    pub fn new() -> IndraConfig {
        // read command line arguments
        let args: Vec<String> = env::args().collect();
        // Check if at least one argument is passed
        if args.len() < 2 {
            println!("Usage: {} <config_file>", args[0]);
            std::process::exit(1);
        }
        // Check if the file exists
        let config_filename = args[1].to_string();
        if !Path::new(&config_filename).exists() {
            println!("File {} does not exist, it should be a TOML file", args[1]);
            std::process::exit(1);
        }

        let toml_str = fs::read_to_string(&config_filename).unwrap();
        let config: IndraConfig = toml::from_str(&toml_str).unwrap();
        return config;
    }
}
