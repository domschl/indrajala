use std::fs;
use toml::Value;

pub struct IndraConfig {
    pub config_filename: String,
    pub toml_str: String,
    pub value: Value,
}

impl IndraConfig {
    pub fn new(config_filename: &str) -> IndraConfig {
        let toml_str = fs::read_to_string(config_filename).unwrap();
        let value = toml_str.parse::<Value>().unwrap();
        let indra_config = IndraConfig {
            config_filename: config_filename.to_string(),
            toml_str,
            value,
        };
        return indra_config;
    }

    pub fn get_value(self, topic: &str, field: &str) -> String {
        let f = self.value[topic][field].as_str().unwrap();
        return f.to_string();
    }
}
