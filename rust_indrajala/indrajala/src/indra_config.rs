use serde::{Deserialize, Serialize};
use std::fs::{self, File};
use std::io::Write;
use std::path::{Path, PathBuf};

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

//#[derive(Deserialize, Clone, Debug)]
//pub struct MqttConfigs {
//    pub mqtt: Vec<MqttConfig>,
//}

#[derive(Deserialize, Clone, Debug)]
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

#[derive(Deserialize, Clone, Debug)]
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
    pub fn new() -> (IndraMainConfig, IndraConfig) {
        // read command line arguments
        let (imc, ctp) = IndraMainConfig::new();
        let config_filename = ctp;
        if !Path::new(&config_filename).exists() {
            println!(
                // XXX default handler
                "File {} does not exist, it should be a TOML file",
                config_filename.to_string_lossy()
            );
            std::process::exit(1);
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
        (imc, cfg)
    }
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct IndraMainConfig {
    pub machine_name: String,
    pub check_internet: bool,
    pub check_internet_interval: u64,
    pub check_internet_max_duration: u64,
    pub data_directory: PathBuf,
    pub default_term_log: String,
    pub default_file_log: String,
}

impl Default for IndraMainConfig {
    fn default() -> Self {
        let hostname = match hostname::get() {
            Ok(h) => h.to_string_lossy().to_string(),
            Err(_) => panic!("Failed to get hostname"),
        };
        IndraMainConfig {
            // get hostname:
            machine_name: hostname,
            check_internet: true,
            check_internet_interval: 5,
            check_internet_max_duration: 60,
            data_directory: dirs::home_dir()
                .unwrap_or(PathBuf::new())
                .join(".local/share/indrajala"),
            default_term_log: "info".to_string(),
            default_file_log: "info".to_string(),
        }
    }
}

impl IndraMainConfig {
    pub fn new() -> (IndraMainConfig, PathBuf) {
        let home_dir = dirs::home_dir().unwrap_or(PathBuf::new());

        let main_config_dir = home_dir.join(".config/indrajala");
        let main_config_path = home_dir.join(".config/indrajala/indra_server.toml");
        let ctp = home_dir.join("./config/indrajala/indra_tasks.toml");

        if main_config_path.exists() {
            let content = fs::read_to_string(main_config_path);
            let imc: Result<IndraMainConfig, _> =
                toml::from_str(content.unwrap_or("".to_string()).as_str());
            match imc {
                Ok(imc) => (imc, ctp),
                Err(_) => (IndraMainConfig::default(), ctp),
            }
        } else {
            let imc = IndraMainConfig::default();
            if !main_config_dir.exists() {
                match fs::create_dir(main_config_dir) {
                    Ok(_) => {}
                    Err(e) => {
                        print!("Failed to create .config/indrajala directory: {}", e);
                        std::process::exit(1);
                    }
                }
            }
            let toml_string = toml::to_string(&imc).unwrap();
            let mut file = File::create(main_config_path).unwrap();
            file.write_all(toml_string.as_bytes()).unwrap();
            (imc, ctp)
        }
    }
}
