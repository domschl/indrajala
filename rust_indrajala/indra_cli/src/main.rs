use serde::{Deserialize, Serialize};
use sqlx::sqlite::SqliteConnection;
use sqlx::Connection;
use std::fs::{self, File};
use std::io::{self, Write};
use std::path::Path;

#[derive(Debug, Serialize, Deserialize, sqlx::FromRow)]
pub struct IndraEvent01 {
    pub domain: String,
    pub from_id: String,
    pub uuid4: String,
    pub to_scope: String,
    pub time_jd_start: f64,
    pub data_type: String,
    pub data: String,
    pub auth_hash: Option<String>,
    pub time_jd_end: Option<f64>,
}

#[derive(Debug, Serialize, Deserialize, sqlx::FromRow)]
pub struct IndraEvent02 {
    pub domain: String,
    pub from_id: String,
    pub uuid4: String,
    pub parent_uuid4: Option<String>,
    pub seq_no: Option<i64>,
    pub to_scope: String,
    pub time_jd_start: f64,
    pub data_type: String,
    pub data: String,
    pub auth_hash: Option<String>,
    pub time_jd_end: Option<f64>,
}

async fn export_records(
    db_path: &str,
    output_json: &str,
    version: &str,
) -> Result<(), sqlx::Error> {
    // Open a connection to the SQLite database
    let mut conn = sqlx::sqlite::SqliteConnection::connect(db_path).await?;

    if version == "01" {
        // Fetch all records from the database
        let records: Vec<IndraEvent01> = sqlx::query_as("SELECT * FROM indra_events")
            .fetch_all(&mut conn)
            .await?;
        // Convert records to JSON
        let json_data = serde_json::to_string(&records).unwrap();

        // Write JSON data to a text file
        let mut file = File::create(output_json)?;
        file.write_all(json_data.as_bytes())?;

        return Ok(());
    } else if version == "02" {
        // Fetch all records from the database
        let records: Vec<IndraEvent02> = sqlx::query_as("SELECT * FROM indra_events")
            .fetch_all(&mut conn)
            .await?;
        // Convert records to JSON
        let json_data = serde_json::to_string(&records).unwrap();

        // Write JSON data to a text file
        let mut file = File::create(output_json)?;
        file.write_all(json_data.as_bytes())?;

        return Ok(());
    }
    Ok(())
}

enum ImportError {
    Sqlx(sqlx::Error),
    Serde(serde_json::Error),
    File(std::io::Error),
}

impl From<sqlx::Error> for ImportError {
    fn from(err: sqlx::Error) -> Self {
        ImportError::Sqlx(err)
    }
}

impl From<serde_json::Error> for ImportError {
    fn from(err: serde_json::Error) -> Self {
        ImportError::Serde(err)
    }
}

impl From<std::io::Error> for ImportError {
    fn from(err: std::io::Error) -> Self {
        ImportError::File(err)
    }
}

async fn import_records(db_path: &str, input_json: &str, version: &str) -> Result<(), ImportError> {
    // Open a connection to the SQLite database
    let mut conn = SqliteConnection::connect(db_path).await?;

    // Read JSON data from the input file
    let json_data = std::fs::read_to_string(input_json)?;

    if version == "01" {
        // Parse JSON data into a vector of IndraEvent01 structs
        let records: Vec<IndraEvent01> = serde_json::from_str(&json_data)?;

        // Insert records into the database
        for record in records {
            sqlx::query(
                "INSERT INTO indra_events (domain, from_id, uuid4, to_scope, time_jd_start, data_type, data, auth_hash, time_jd_end)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            )
            .bind(&record.domain)
            .bind(&record.from_id)
            .bind(&record.uuid4)
            .bind(&record.to_scope)
            .bind(record.time_jd_start)
            .bind(&record.data_type)
            .bind(&record.data)
            .bind(&record.auth_hash)
            .bind(record.time_jd_end)
            .execute(&mut conn)
            .await?;
        }
    } else if version == "02" {
        // Parse JSON data into a vector of IndraEvent02 structs
        let records: Vec<IndraEvent02> = serde_json::from_str(&json_data)?;

        // Insert records into the database
        for record in records {
            sqlx::query(
                "INSERT INTO indra_events (domain, from_id, uuid4, parent_uuid4, seq_no, to_scope, time_jd_start, data_type, data, auth_hash, time_jd_end)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            )
            .bind(&record.domain)
            .bind(&record.from_id)
            .bind(&record.uuid4)
            .bind(&record.parent_uuid4)
            .bind(record.seq_no)
            .bind(&record.to_scope)
            .bind(record.time_jd_start)
            .bind(&record.data_type)
            .bind(&record.data)
            .bind(&record.auth_hash)
            .bind(record.time_jd_end)
            .execute(&mut conn)
            .await?;
        }
    }

    Ok(())
}
/*
fn main() {
      let rt = async_std::task::block_on(export_records("01"));
      if let Err(e) = rt {
          eprintln!("Error: {}", e);
      }
  }
  */

const DEFAULTS_FILE: &str = ".config/indrajala/cli_state.toml";

#[derive(Debug, Clone, Serialize, Deserialize)]
struct IndraClientConfig {
    uri: String,
    version: String,
    db_path: String,
    output_path: String,
    mode: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct IndraCli {
    connected: bool,
    cfg: IndraClientConfig,
}

impl IndraCli {
    fn new() -> Result<IndraCli, Box<dyn std::error::Error>> {
        let connected = false;
        let mut cfg = IndraClientConfig {
            uri: "".to_string(),
            version: "".to_string(),
            db_path: "".to_string(),
            output_path: "indra_backup.json".to_string(),
            mode: "offline".to_string(),
        };
        cfg = IndraCli::load_defaults(&cfg);
        Ok(IndraCli { connected, cfg })
    }

    fn load_defaults(cfg: &IndraClientConfig) -> IndraClientConfig {
        let home_dir = dirs::home_dir().ok_or_else(|| cfg.clone());
        let defaults_file_path = home_dir.unwrap().join(DEFAULTS_FILE);

        if defaults_file_path.exists() {
            let defaults_content =
                fs::read_to_string(&defaults_file_path).unwrap_or("".to_string());
            return toml::from_str(&defaults_content).unwrap_or(cfg.clone());
        }
        cfg.clone()
    }

    fn save_defaults(&self) -> Result<(), Box<dyn std::error::Error>> {
        let home_dir = dirs::home_dir().ok_or("Failed to determine home directory")?;
        let defaults_file_path = home_dir.join(DEFAULTS_FILE);

        let defaults_content = toml::to_string_pretty(&self.cfg)?;
        fs::create_dir_all(Path::new(&defaults_file_path).parent().unwrap())?;
        fs::write(defaults_file_path, defaults_content)?;

        Ok(())
    }

    fn update_default(&mut self, variable: &str, value: &str) {
        match variable {
            "uri" => self.cfg.uri = value.to_string(),
            "version" => self.cfg.version = value.to_string(),
            "db_path" => self.cfg.db_path = value.to_string(),
            "output_path" => self.cfg.output_path = value.to_string(),
            "mode" => self.cfg.mode = value.to_string(),
            _ => println!("Invalid variable: {}", variable),
        }
    }

    fn connect(&mut self, uri: &str) {
        self.connected = true;
        self.cfg.uri = uri.to_string();
        println!("Connected to: {}", uri);
    }

    fn disconnect(&mut self) {
        self.connected = false;
        println!("Disconnected");
    }

    fn backup(&self, version: &str, db_path: &str, output_json: &str, confirm: bool) {
        if confirm {
            // Prompt the user to confirm the backup operation
            print!(
                "Are you sure you want to backup the database {}, version {} to file {}? (y/n) ",
                db_path, version, output_json
            );
            io::stdout().flush().unwrap();

            let mut input = String::new();
            io::stdin().read_line(&mut input).unwrap();

            if input.trim().to_lowercase() == "y" {
                // Perform the backup operation
                println!("Starting backup...");
                let rt = async_std::task::block_on(export_records(db_path, output_json, version));
                if let Err(e) = rt {
                    eprintln!("Error: {}", e);
                } else {
                    println!("Backup completed successfully.");
                }
            } else {
                println!("Backup cancelled.");
            }
        }
    }

    fn restore(&self, version: &str, output: &str, input: &str) {
        println!(
            "Restore: version={}, output={}, input={}",
            version, output, input
        );
    }

    fn print_state(&self) {
        println!(
            "Connected: {}\nConnection URL: {}\nVersion: {}\nDB Path: {}\nOutput Path: {}\nMode: {}",
            self.connected, self.cfg.uri, self.cfg.version, self.cfg.db_path, self.cfg.output_path, self.cfg.mode
        );
    }

    fn process_command(&mut self, command: &str) -> bool {
        let parts: Vec<&str> = command.split_whitespace().collect();

        match parts[0] {
            "connect" => {
                if parts.len() == 1 {
                    self.clone().connect(self.cfg.uri.as_str());
                } else {
                    println!("Invalid command. Usage: connect=<url>");
                }
            }
            "disconnect" => {
                self.disconnect();
            }
            "backup" => {
                let mut version = self.cfg.version.as_str();
                let mut input = self.cfg.db_path.as_str();
                let mut output = self.cfg.output_path.as_str();

                for part in parts.iter().skip(1) {
                    if part.starts_with("version=") {
                        version = part.split_at(8).1;
                    } else if part.starts_with("input=") {
                        input = part.split_at(6).1;
                    } else if part.starts_with("output=") {
                        output = part.split_at(7).1;
                    }
                }

                self.backup(version, input, output, true);
            }
            "restore" => {
                let mut version = self.cfg.version.as_str();
                let mut output = self.cfg.db_path.as_str();
                let mut input = self.cfg.output_path.as_str();

                for part in parts.iter().skip(1) {
                    if part.starts_with("version=") {
                        version = part.split_at(8).1;
                    } else if part.starts_with("output=") {
                        output = part.split_at(7).1;
                    } else if part.starts_with("input=") {
                        input = part.split_at(6).1;
                    }
                }

                self.restore(version, output, input);
            }
            "state" => {
                self.print_state();
            }
            "help" => {
                println!("Available commands:\n- connect\n- disconnect\n- backup\n- restore\n- state\n- help\n- exit");
            }
            "exit" => {
                return false;
            }
            _ => {
                let mut variable = "";
                let mut value = "";

                if let Some(index) = parts[0].find('=') {
                    variable = parts[0].split_at(index).0;
                    value = &parts[0][index + 1..];
                }
                if !variable.is_empty() && !value.is_empty() {
                    self.update_default(variable, value);
                    self.save_defaults().unwrap();
                } else {
                    println!("Invalid command");
                }
            }
        }

        self.connected
    }

    fn run_repl(&mut self) {
        loop {
            print!("ic> ");
            io::stdout().flush().unwrap();

            let mut command = String::new();
            io::stdin().read_line(&mut command).unwrap();

            if command.trim() == "exit" {
                break;
            }

            self.process_command(command.trim());
        }
    }
}

fn main() {
    let mut indra_cli = IndraCli::new().unwrap();
    let args: Vec<String> = std::env::args().collect();

    if args.len() > 1 {
        let action = &args[1];
        if action == "help" {
            println!("Available commands:\n- connect\n- disconnect\n- backup\n- restore\n- state\n- help\n- exit");
        } else {
            let mut variables = Vec::new();

            for arg in args.iter().skip(2) {
                if let Some(index) = arg.find('=') {
                    let variable = &arg[..index];
                    let value = &arg[index + 1..];
                    variables.push((variable.to_string(), value.to_string()));
                } else {
                    println!("Invalid argument: {}", arg);
                    return;
                }
            }

            for (variable, value) in variables {
                indra_cli.update_default(&variable, &value);
            }

            indra_cli.save_defaults().unwrap();

            indra_cli.process_command(action);
        }
    } else {
        indra_cli.run_repl();
    }
}
