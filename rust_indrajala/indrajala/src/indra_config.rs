use serde::Deserialize;
use std::env;
use std::fs;
use std::path::Path;
use toml;
//use env_logger::Env;
//use log::{debug, error, info, warn};

#[derive(Deserialize, Clone, Debug)]
pub struct IndraConfig {
    pub mqtt: Option<Vec<MqttConfig>>,
    pub ding_dong: Option<Vec<DingDongConfig>>,
    pub web: Option<Vec<WebConfig>>,
    pub sqlx: Option<Vec<SQLxConfig>>,
    pub ws: Option<Vec<WsConfig>>,
    pub signal: Option<Vec<SignalConfig>>,
    pub tasker: Option<Vec<TaskerConfig>>,
}

/*
#[derive(Deserialize, Clone, Debug)]
pub struct IndraTaskConfigs {
    pub tasks: Vec<IndraTaskConfig>,
}
*/
#[derive(Deserialize, Clone, Copy, Debug)]
pub enum TaskCapability {
    Send,
    Receive,
    Request,
}

#[derive(Deserialize, Clone, Debug)]
pub struct MqttConfig {
    pub name: String,
    pub active: bool,
    pub capa: Vec<TaskCapability>,
    pub host: String,
    pub port: u16,
    pub username: String,
    pub password: String,
    pub client_id: String,
    pub to_scope: String,
    pub topics: Vec<String>,
    pub out_topics: Vec<String>,
    pub out_blocks: Vec<String>,
}

#[derive(Deserialize, Clone, Debug)]
pub struct MqttConfigs {
    pub mqtt: Vec<MqttConfig>,
}

#[derive(Deserialize, Clone, Debug)]
pub struct DingDongConfig {
    pub name: String,
    pub active: bool,
    pub capa: Vec<TaskCapability>,
    pub timer: u64,
    pub topic: String,
    pub message: String,
    pub out_topics: Vec<String>,
    pub out_blocks: Vec<String>,
}

#[derive(Deserialize, Clone, Debug)]
pub struct SignalConfig {
    pub name: String,
    pub active: bool,
    pub shutdown_delay_ms: u64,
    pub capa: Vec<TaskCapability>,
    pub out_topics: Vec<String>,
    pub out_blocks: Vec<String>,
}

#[derive(Deserialize, Clone, Debug)]
pub struct WebConfig {
    pub name: String,
    pub active: bool,
    pub capa: Vec<TaskCapability>,
    pub address: String,
    pub url: String,
    pub ssl: bool,
    pub cert: String,
    pub key: String,
    pub out_topics: Vec<String>,
    pub out_blocks: Vec<String>,
}

#[derive(Deserialize, Clone, Debug)]
pub struct WsConfig {
    pub name: String,
    pub active: bool,
    pub capa: Vec<TaskCapability>,
    pub address: String,
    pub url: String,
    pub ssl: bool,
    pub cert: String,
    pub key: String,
    pub out_topics: Vec<String>,
    pub out_blocks: Vec<String>,
}

#[derive(Deserialize, Clone, Debug)]
pub enum DbType {
    Postgres,
    MySQL,
    SQLite,
}

#[derive(Deserialize, Clone, Debug)]
pub enum DbSync {
    Sync,
    Async,
}

#[derive(Deserialize, Clone, Debug)]
pub struct SQLxConfig {
    pub name: String,
    pub active: bool,
    pub capa: Vec<TaskCapability>,
    pub db_type: DbType,
    pub db_sync: DbSync,
    pub database_url: String,
    pub out_topics: Vec<String>,
    pub out_blocks: Vec<String>,
}

#[derive(Deserialize, Clone, Debug)]
pub enum TaskerMode {
    Periodic,
    Oneshot,
    Continuous,
}
#[derive(Deserialize, Clone, Debug)]
pub enum TaskerIpc {
    Stdio,
    Net,
}
#[derive(Deserialize, Clone, Debug)]
pub struct TaskerConfig {
    pub name: String,
    pub active: bool,
    pub capa: Vec<TaskCapability>,
    pub cmd: String,
    pub args: Vec<String>,
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

        let toml_string = fs::read_to_string(config_filename).unwrap();
        let toml_str = toml_string.as_str();

        let cfg: IndraConfig = toml::from_str(toml_str).unwrap();
        cfg
    }
}
