use serde::{Deserialize, Serialize};
use sqlx::Connection;
use std::fs::File;
use std::io::Write;

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

async fn export_records(version: &str) -> Result<(), sqlx::Error> {
    // Open a connection to the SQLite database
    let mut conn = sqlx::sqlite::SqliteConnection::connect("config/db/indrajala.db").await?;

    if version == "01" {
        // Fetch all records from the database
        let records: Vec<IndraEvent01> = sqlx::query_as("SELECT * FROM indra_events")
            .fetch_all(&mut conn)
            .await?;
        // Convert records to JSON
        let json_data = serde_json::to_string(&records).unwrap();

        // Write JSON data to a text file
        let mut file = File::create("indra_export.json")?;
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
        let mut file = File::create("indra_export.json")?;
        file.write_all(json_data.as_bytes())?;

        return Ok(());
    }
    Ok(())
}

fn main() {
    let rt = async_std::task::block_on(export_records("01"));
    if let Err(e) = rt {
        eprintln!("Error: {}", e);
    }
}
