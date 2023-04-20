use serde::Deserialize;
use std::env;
use std::fs;
use std::path::Path;

//use std::collections::HashMap;
use toml::Value;

/* #[derive(Deserialize, Clone)]
pub struct IndraConfig {
    pub mqtt: MqttConfig,
    pub dingdong: DingDongConfig,
    pub rest: RestConfig,
    pub sqlx: SQLxConfig,
} */

pub enum IndraTaskConfig {
    MqttConfig,
    DingDongConfig,
    RestConfig,
    SQLxConfig,
}

#[derive(Deserialize, Clone)]
pub enum TaskCapability {
    Send,
    Receive,
    Request,
}

#[derive(Deserialize, Clone)]
pub struct MqttConfig {
    pub name: String,
    pub active: bool,
    pub capa: TaskCapability,
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
    pub name: String,
    pub active: bool,
    pub capa: TaskCapability,
    pub timer: u64,
    pub topic: String,
    pub message: String,
    pub out_topics: Vec<String>,
    pub out_blocks: Vec<String>,
}

#[derive(Deserialize, Clone)]
pub struct RestConfig {
    pub name: String,
    pub active: bool,
    pub capa: TaskCapability,
    pub address: String,
    pub url: String,
    pub ssl: bool,
    pub cert: String,
    pub key: String,
    pub out_topics: Vec<String>,
    pub out_blocks: Vec<String>,
}

#[derive(Deserialize, Clone)]
pub enum DbType {
    Postgres,
    MySQL,
    SQLite,
}

#[derive(Deserialize, Clone)]
pub struct SQLxConfig {
    pub name: String,
    pub active: bool,
    pub capa: TaskCapability,
    pub db_type: DbType,
    pub database_url: String,
    pub out_topics: Vec<String>,
    pub out_blocks: Vec<String>,
}

/*
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
 */

impl IndraTaskConfig {
    // pub fn new() -> IndraTaskConfig {}

    pub fn read_tasks() -> Vec<IndraTaskConfig> {
        let tasks: Vec<IndraTaskConfig> = Vec::new();
        let toml_str = fs::read_to_string("config/indra_tasks.toml").unwrap();
        let value = toml_str.parse::<Value>().unwrap();

        if let Value::Table(table) = value {
            for (section_name, section_value) in table {
                println!("----------------------------------");
                println!("[{}]", section_name);
                // println!("section_table = {:#?}", section_value);
                let task_entries = section_value.as_array();
                if let Some(task_entries) = task_entries {
                    // .as_table().unwrap();
                    for section in task_entries {
                        println!("---- {} -----", section["name"]);
                        println!("{:#?}", section);
                    }
                }
                /*
                if let Value::Table(section_table) = section_value {
                    for (key, value) in section_table {
                        println!("{} = {}", key, value);
                    }
                } */
            }
        }
        tasks
    }
}
