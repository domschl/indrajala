use std::env;
use std::fs;
use std::path::Path;
use toml::Value;

pub struct IndraConfig {
    pub config_filename: String,
    pub toml_str: String,
    pub value: Value,
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
        let value = toml_str.parse::<Value>().unwrap();
        let indra_config = IndraConfig {
            config_filename: config_filename,
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
