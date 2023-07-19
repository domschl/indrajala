use serde::{Deserialize, Serialize};
use std::env::consts::OS;
use std::fs::{self, File};
use std::io::Write;
use std::path::{Path, PathBuf};

#[derive(Deserialize, Serialize, Clone, Debug)]
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

impl Default for IndraConfig {
    fn default() -> Self {
        IndraConfig {
            mqtt: Some(vec![MqttConfig::default()]),
            ding_dong: Some(vec![DingDongConfig::default()]),
            web: Some(vec![WebConfig::default()]),
            sqlx: Some(vec![SQLxConfig::default()]),
            ws: Some(vec![WsConfig::default()]),
            signal: Some(vec![SignalConfig::default()]),
            tasker: Some(vec![TaskerConfig::default()]),
            llm: Some(vec![LLMConfig::default()]),
        }
    }
}
#[derive(Deserialize, Serialize, Clone, Debug)]
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

impl Default for MqttConfig {
    fn default() -> Self {
        MqttConfig {
            name: "MQTT.1".to_string(),
            active: false,
            host: "localhost".to_string(),
            port: 1883,
            username: "".to_string(),
            password: "".to_string(),
            client_id: "indra_{{machine_name}}".to_string(),
            to_scope: "home".to_string(),
            topics: vec!["#".to_string()],
        }
    }
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct DingDongConfig {
    pub name: String,
    pub active: bool,
    pub timer: u64,
    pub topic: String,
    pub message: String,
}

impl Default for DingDongConfig {
    fn default() -> Self {
        DingDongConfig {
            name: "DingDong.1".to_string(),
            active: false,
            timer: 1000,
            topic: "Ding".to_string(),
            message: "Dong".to_string(),
        }
    }
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct SignalConfig {
    pub name: String,
    pub active: bool,
    pub shutdown_delay_ms: u64,
}

impl Default for SignalConfig {
    fn default() -> Self {
        SignalConfig {
            name: "Signal.1".to_string(),
            active: true,
            shutdown_delay_ms: 1000,
        }
    }
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct WebConfig {
    pub name: String,
    pub active: bool,
    pub address: String,
    pub url: String,
    pub ssl: bool,
    pub cert: String,
    pub key: String,
}

impl Default for WebConfig {
    fn default() -> Self {
        WebConfig {
            name: "Web.1".to_string(),
            active: false,
            address: "0.0.0.0:8081".to_string(),
            url: "/api/v1".to_string(),
            ssl: true,
            cert: "{{data_directory}}/certs/{{machine_name}}.pem".to_string(),
            key: "{{data_directory}}/certs/{{machine_name}}-key.pem".to_string(),
        }
    }
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct WsConfig {
    pub name: String,
    pub active: bool,
    pub address: String,
    pub url: String,
    pub ssl: bool,
    pub cert: String,
    pub key: String,
}

impl Default for WsConfig {
    fn default() -> Self {
        WsConfig {
            name: "Ws.1".to_string(),
            active: false,
            address: "0.0.0.0:8082".to_string(),
            url: "/ws/v1".to_string(),
            ssl: true,
            cert: "{{data_directory}}/certs/{{machine_name}}.pem".to_string(),
            key: "{{data_directory}}/certs/{{machine_name}}-key.pem".to_string(),
        }
    }
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub enum DbType {
    Postgres,
    MySQL,
    SQLite,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub enum DbSync {
    Sync,
    Async,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct SQLxConfig {
    pub name: String,
    pub active: bool,
    pub db_type: DbType,
    pub db_sync: DbSync,
    pub database_url: String,
    pub last_state_file: String,
    pub persistent_domains: Vec<String>,
    pub volatile_domains: Vec<String>,
}

impl Default for SQLxConfig {
    fn default() -> Self {
        SQLxConfig {
            name: "SQLx.1".to_string(),
            active: false,
            db_type: DbType::SQLite,
            db_sync: DbSync::Async,
            database_url: "{{data_directory}}/db/indrajala.db".to_string(),
            last_state_file: "{{data_directory}}/db/last_state.json".to_string(),
            persistent_domains: vec!["$event/".to_string()],
            volatile_domains: vec!["$forecast/".to_string()],
        }
    }
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub enum TaskerMode {
    Periodic,
    Oneshot,
    Continuous,
}
#[derive(Deserialize, Serialize, Clone, Debug)]
pub enum TaskerIpc {
    Stdio,
    Net,
}
#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct TaskerConfig {
    pub name: String,
    pub active: bool,
    pub cmd: String,
    pub args: Vec<String>,
}

impl Default for TaskerConfig {
    fn default() -> Self {
        TaskerConfig {
            name: "Tasker.1".to_string(),
            active: false,
            cmd: "echo".to_string(),
            args: vec!["Hello World".to_string()],
        }
    }
}

#[derive(Deserialize, Serialize, Clone, Debug)]
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

impl Default for LLMConfig {
    fn default() -> Self {
        LLMConfig {
            name: "LLM.1".to_string(),
            active: false,
            model_path: "{{data_directory}}/models/llm".to_string(),
            model_arch: "llama".to_string(),
            model_overrides: "{}".to_string(),
            tokenizer_path: None,
            tokenizer_repo: None,
            prefer_mmap: Some(true),
            context_size: Some(2048),
            use_gpu: Some(false),
            lora_paths: None,
            n_threads: None,
            n_batch: None,
            top_k: None,
            top_p: None,
            repeat_penalty: None,
            temperature: None,
            repetition_penalty_last_n: None,
            no_float16: None,
        }
    }
}

impl IndraConfig {
    pub fn new() -> (IndraMainConfig, IndraConfig, String) {
        let (imc, ctp) = IndraMainConfig::new();
        let config_filename = ctp;
        let mut state_msg = "".to_string();
        if !Path::new(&config_filename).exists() {
            // create default file
            let mut file = File::create(&config_filename).unwrap();
            let toml_string = toml::to_string_pretty(&IndraConfig::default()).unwrap();
            file.write_all(toml_string.as_bytes()).unwrap();
            state_msg = format!(
                "Created default config file at {}",
                config_filename.to_string_lossy()
            );
        }
        let toml_string = fs::read_to_string(config_filename).unwrap();
        // replace {{data_directory}} with the actual data directory
        let toml_string = toml_string.replace(
            "{{data_directory}}",
            imc.data_directory.to_string_lossy().as_ref(),
        );
        // replace {{machine_name}} with the actual machine name
        let toml_string = toml_string.replace("{{machine_name}}", &imc.machine_name);

        let toml_str = toml_string.as_str();

        let cfg: IndraConfig = toml::from_str(toml_str).unwrap();
        (imc, cfg, state_msg)
    }
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct IndraMainConfig {
    pub machine_name: String,
    pub check_internet: bool,
    pub check_internet_interval: u64,
    pub check_internet_max_duration: u64,
    pub config_directory: PathBuf,
    pub data_directory: PathBuf,
    pub default_term_log: String,
    pub default_file_log: String,
}

impl Default for IndraMainConfig {
    fn default() -> Self {
        let hostname = match hostname::get() {
            Ok(h) => {
                h.to_string_lossy().to_string();
                // remove domain name
                let mut hn = h.to_string_lossy().to_string();
                if let Some(pos) = hn.find('.') {
                    hn.truncate(pos);
                }
                hn
            }
            Err(_) => panic!("Failed to get hostname"),
        };
        // check, if linux os and root user:
        //if OS == "linux" {
        //    // check for root user:
        //
        //} else {
        //    let data_path = '.local/share/indrajala';
        //}

        let data_directory = {
            if OS == "linux" {
                PathBuf::from("/var/lib/indrajala")
            } else {
                dirs::home_dir()
                    .unwrap_or(PathBuf::new())
                    .join(".local/share/indrajala")
            }
        };

        IndraMainConfig {
            // get hostname:
            machine_name: hostname,
            check_internet: true,
            check_internet_interval: 5,
            check_internet_max_duration: 60,
            config_directory: "".into(),
            data_directory,
            default_term_log: "info".to_string(),
            default_file_log: "info".to_string(),
        }
    }
}

impl IndraMainConfig {
    pub fn new() -> (IndraMainConfig, PathBuf) {
        let mut config_path: PathBuf = PathBuf::new();
        if OS == "linux" {
            config_path = PathBuf::from("/etc/indrajala");
            if !config_path.exists() {
                config_path.clear();
            }
        }
        if config_path.to_string_lossy().as_ref().is_empty() {
            config_path = dirs::home_dir()
                .unwrap_or(PathBuf::new())
                .join(".config/indrajala");
            if !config_path.exists() {
                match fs::create_dir(&config_path) {
                    Ok(_) => {}
                    Err(e) => {
                        print!("Failed to create ~/.config/indrajala directory: {}", e);
                        std::process::exit(1);
                    }
                }
            }
        }
        let main_config_file = config_path.join("indra_server.toml");
        let tasks_file = config_path.join("indra_tasks.toml");
        if main_config_file.exists() {
            let content = fs::read_to_string(&main_config_file);
            let imc: Result<IndraMainConfig, _> =
                toml::from_str(content.unwrap_or("".to_string()).as_str());
            match imc {
                Ok(imc) => (imc, tasks_file),
                Err(e) => {
                    print!(
                        "Failed to parse main config file {}: {}",
                        main_config_file.to_string_lossy(),
                        e
                    );
                    std::process::exit(1);
                }
            }
        } else {
            let imc = IndraMainConfig {
                config_directory: config_path,
                ..Default::default()
            };
            let toml_string = toml::to_string(&imc).unwrap();
            let mut file = File::create(&main_config_file).unwrap();
            file.write_all(toml_string.as_bytes()).unwrap();
            (imc, tasks_file)
        }
    }
}
