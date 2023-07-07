use serde::Deserialize;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
//use toml;
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
    pub llm: Option<Vec<LLMConfig>>,
}

#[derive(Deserialize, Clone, Debug)]
pub struct MqttConfig {
    pub name: String,
    pub active: bool,
    pub host: String,
    pub port: u16,
    pub username: String,
    pub password: String,
    pub client_id: String,
    pub to_scope: String,
    pub topics: Vec<String>,
}

#[derive(Deserialize, Clone, Debug)]
pub struct MqttConfigs {
    pub mqtt: Vec<MqttConfig>,
}

#[derive(Deserialize, Clone, Debug)]
pub struct DingDongConfig {
    pub name: String,
    pub active: bool,
    pub timer: u64,
    pub topic: String,
    pub message: String,
}

#[derive(Deserialize, Clone, Debug)]
pub struct SignalConfig {
    pub name: String,
    pub active: bool,
    pub shutdown_delay_ms: u64,
}

#[derive(Deserialize, Clone, Debug)]
pub struct WebConfig {
    pub name: String,
    pub active: bool,
    pub address: String,
    pub url: String,
    pub ssl: bool,
    pub cert: String,
    pub key: String,
}

#[derive(Deserialize, Clone, Debug)]
pub struct WsConfig {
    pub name: String,
    pub active: bool,
    pub address: String,
    pub url: String,
    pub ssl: bool,
    pub cert: String,
    pub key: String,
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
    pub db_type: DbType,
    pub db_sync: DbSync,
    pub database_url: String,
    pub last_state_file: String,
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
    pub cmd: String,
    pub args: Vec<String>,
}

#[derive(Deserialize, Clone, Debug)]
pub struct LLMConfig {
    pub name: String,
    pub active: bool,
    pub model_path: String,
    pub model_arch: String,
    pub model_overrides: String,
    pub tokenizer_path: Option<String>,
    pub tokenizer_repo: Option<String>,
    pub prefer_mmap: Option<bool>,
    pub context_size: Option<usize>,
    pub use_gpu: Option<bool>,
    pub lora_paths: Option<Vec<PathBuf>>,
    pub n_threads: Option<usize>,
    pub n_batch: Option<usize>,
    pub top_k: Option<usize>,
    pub top_p: Option<f32>,
    pub repeat_penalty: Option<f32>,
    pub temperature: Option<f32>,
    pub repetition_penalty_last_n: Option<usize>,
    pub no_float16: Option<bool>,
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
