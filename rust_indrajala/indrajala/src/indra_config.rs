use serde::Deserialize;
use std::env;
use std::fs;
use std::path::Path;

#[derive(Deserialize, Clone)]
pub struct IndraConfig {
    pub mqtt: MqttConfig,
    pub dingdong: DingDongConfig,
    pub rest: RestConfig,
    pub sqlx: SQLxConfig,
}

#[derive(Deserialize, Clone)]
pub struct MqttConfig {
    pub active: bool,
    pub host: String,
    pub port: u16,
    pub username: String,
    pub password: String,
    pub client_id: String,
    pub topics: Vec<String>,
    pub out_topics: Vec<String>,
    pub out_blocks: Vec<String>,
}

#[derive(Deserialize, Clone)]
pub struct DingDongConfig {
    pub active: bool,
    pub timer: u64,
    pub topic: String,
    pub message: String,
    pub out_topics: Vec<String>,
    pub out_blocks: Vec<String>,
}

#[derive(Deserialize, Clone)]
pub struct RestConfig {
    pub active: bool,
    pub address: String,
    pub url: String,
    pub ssl: bool,
    pub cert: String,
    pub key: String,
    pub out_topics: Vec<String>,
    pub out_blocks: Vec<String>,
}

#[derive(Deserialize, Clone)]
pub struct SQLxConfig {
    pub active: bool,
    pub database_url: String,
    pub out_topics: Vec<String>,
    pub out_blocks: Vec<String>,
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