use async_std::task;
use chrono::Utc;
use indra_event::{
    IndraEvent, IndraHistoryRequest, IndraHistoryRequestMode, IndraUniqueDomainsRequest,
};
use serde::{Deserialize, Serialize};
use sqlx::sqlite::{SqliteConnectOptions, SqlitePool};
use sqlx::Row;
use std::fs;
use std::fs::File;
use std::io::Write;
use std::path::PathBuf;
use std::time::Duration;

//use std::path::Path;

//use env_logger::Env;
//use log::{debug, error, info, warn};
use log::{debug, error, info, warn};

use crate::indra_config::{DbSync, StorageConfig};
use crate::AsyncIndraTask;

#[derive(Deserialize, Serialize, Debug, Clone)]
pub struct LastState {
    pub last_seq_no: i64,
}

#[derive(Clone)]
pub struct Storage {
    pub config: StorageConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
    pub sender: async_channel::Sender<IndraEvent>,
    pub subs: Vec<String>,
    pub pool: Option<SqlitePool>,
    pub last_state: LastState,
    pub r_sender: Option<async_channel::Sender<IndraEvent>>,
}

impl Storage {
    pub fn new(mut config: StorageConfig) -> Self {
        let s1: async_channel::Sender<IndraEvent>;
        let r1: async_channel::Receiver<IndraEvent>;
        (s1, r1) = async_channel::unbounded();
        //let sq_config = config.clone();
        let def_addr = "$trx/db/#".to_string();
        let mut subs = vec![def_addr, format!("{}/#", config.name)];
        // add persistent and volatile domains to subscriptions:
        for per_dom in config.persistent_domains.iter() {
            if !subs.contains(per_dom) {
                subs.push(per_dom.clone());
            }
        }
        for vol_dom_dur in config.volatile_domains.iter() {
            let vol_dom = vol_dom_dur.0.clone();
            //let vol_dom_subs = format!("{}/#", vol_dom);
            // check if vol_dom_subs is already in subs:
            if !subs.contains(&vol_dom) {
                subs.push(vol_dom);
            }
        }

        task::block_on(async {
            let db_dir = PathBuf::from(config.database_directory.clone());
            let last_state_path = db_dir.join("last_state.json");
            let mut last_state: LastState;
            //let last_state_path: PathBuf = PathBuf::from(stnam);
            let last_state_exists: bool = last_state_path.exists();
            if last_state_exists {
                let last_state_str: String =
                    fs::read_to_string(last_state_path.clone()).unwrap_or("".to_string());
                last_state =
                    serde_json::from_str(&last_state_str).unwrap_or(LastState { last_seq_no: 0 });
            } else {
                last_state = LastState { last_seq_no: 0 };
            }
            let pool = Storage::async_init(&mut config, last_state.last_seq_no).await;
            if pool.is_some() {
                last_state.last_seq_no =
                    Storage::read_last_seq_no(&pool.clone().unwrap(), last_state.last_seq_no).await;
            }
            Storage {
                config: config.clone(),
                receiver: r1,
                sender: s1,
                subs,
                pool,
                last_state,
                r_sender: Default::default(),
            }
        })
    }

    async fn read_last_seq_no(pool: &SqlitePool, old_last_seq_no: i64) -> i64 {
        // Read highest value of seq_no from the database
        let mut last_seq_no: i64;
        let q_res3 = sqlx::query("SELECT seq_no FROM indra_events ORDER BY seq_no DESC LIMIT 1;");
        let q_res3 = q_res3.fetch_one(&pool.clone()).await;
        match q_res3 {
            Ok(q_res3) => {
                last_seq_no = q_res3.try_get(0).unwrap_or(0);
                if last_seq_no < old_last_seq_no {
                    last_seq_no = old_last_seq_no;
                }
                debug!(
                    "Storage::init: last_seq_no from database: {} from state_file: {}",
                    last_seq_no, old_last_seq_no
                );
            }
            Err(e) => {
                last_seq_no = old_last_seq_no;
                info!(
                    "Storage::init: Error reading last_seq_no: {:?}, current last_seq_no is {}",
                    e, last_seq_no
                );
            }
        }
        last_seq_no
    }

    async fn check_column_exists(
        pool: &SqlitePool,
        table_name: &str,
        column_name: &str,
    ) -> Result<bool, sqlx::Error> {
        #[derive(Debug, sqlx::FromRow)]
        struct TableInfo {
            name: String,
            // Add other fields as needed from the table_info result
        }
        // info!(
        //     "Checking if column {} exists in table {}",
        //    column_name, table_name
        //);
        let schema_query = format!("PRAGMA table_info({})", table_name);
        let columns: Vec<TableInfo> = sqlx::query_as(&schema_query).fetch_all(pool).await?;
        // info!("Columns: {:?}", columns);
        // Check if the column exists
        let exists = columns.iter().any(|column| column.name == column_name);
        Ok(exists)
    }

    async fn add_seq_no_column(pool: &SqlitePool, seq_no_init: i64) -> Result<(), sqlx::Error> {
        // Add the seq_no column to the table
        let add_column_query =
            "ALTER TABLE indra_events ADD COLUMN seq_no INTEGER NOT NULL DEFAULT 0";
        sqlx::query(add_column_query).execute(pool).await?;

        // Update each record with a sequentially incremented value for seq_no
        let update_query = "UPDATE indra_events SET seq_no = ? + rowid";
        sqlx::query(update_query)
            .bind(seq_no_init)
            .execute(pool)
            .await?;

        Ok(())
    }

    async fn async_init(config: &mut StorageConfig, sq_no: i64) -> Option<SqlitePool> {
        let db_dir = PathBuf::from(config.database_directory.clone());
        // check if exists:
        if !db_dir.exists() {
            // create it:
            match fs::create_dir_all(db_dir.clone()) {
                Ok(_) => {
                    info!(
                        "Storage::init: Created database directory {}",
                        db_dir.to_string_lossy()
                    );
                }
                Err(e) => {
                    error!(
                        "Storage::init: Error creating database directory {}: {:?}",
                        db_dir.to_string_lossy(),
                        e
                    );
                    config.active = false;
                    return None;
                }
            }
        }
        let db_file = "indrajala.db";
        // concat db_dir and db_file:
        let fnam = db_dir.join(db_file);
        let db_sync: &str = match config.db_sync {
            DbSync::Sync => "NORMAL",
            DbSync::Async => "OFF",
        };
        let options = SqliteConnectOptions::new()
            .filename(fnam.clone())
            .create_if_missing(true)
            .pragma("journal_mode", "WAL") // alternative: DELETE, TRUNCATE, PERSIST, MEMORY, OFF
            //  This line sets the page size of the memory to 4096 bytes. This is the size of a single page in the memory.
            // You can change this if you want to, but please be aware that the page size must be a power of 2.
            // For example, 1024, 2048, 4096, 8192, 16384, etc.
            .pragma("page_size", "4096")
            //  This is the number of pages that will be cached in memory. If you have a lot of memory, you can increase
            // this number to improve performance. If you have a small amount of memory, you can decrease this number to free up memory.
            .pragma("cache_size", "10000")
            // This means that the database will be synced to disk after each transaction. If you don't want this, you can set it to off.
            // However, please be aware that this will make your database more vulnerable to corruption.
            .pragma("synchronous", db_sync) // alternative: OFF, NORMAL, FULL, EXTRA
            .pragma("temp_store", "memory") // alternative: FILE
            .pragma("mmap_size", "1073741824"); // 1Galternative: any positive integer
        let mut pool: Option<SqlitePool>;
        let pool_res = sqlx::SqlitePool::connect_with(options).await;
        match pool_res {
            Ok(pool_res) => {
                info!(
                    "Storage::init: Connected to database {}",
                    fnam.to_string_lossy()
                );
                pool = Some(pool_res);
            }
            Err(e) => {
                error!(
                    "Storage::init: Error connecting to database {}: {:?}",
                    fnam.to_string_lossy(),
                    e
                );
                config.active = false;
                pool = None;
                return pool;
            }
        }
        // let pool = self.pool.clone().unwrap();

        // Create a new table
        let q_res = sqlx::query(
            r#"
                    CREATE TABLE IF NOT EXISTS indra_events (
                        id INTEGER PRIMARY KEY,
                        seq_no INTEGER NOT NULL,
                        domain TEXT NOT NULL,
                        from_id TEXT NOT NULL,
                        uuid4 UUID NOT NULL,
                        parent_uuid4 UUID,
                        to_scope TEXT NOT NULL,
                        time_jd_start DOUBLE,
                        data_type TEXT NOT NULL,
                        data TEXT NOT NULL,
                        auth_hash TEXT,
                        time_jd_end DOUBLE
                    )
                    "#,
        )
        .execute(&pool.clone().unwrap())
        .await;
        match q_res {
            Ok(_) => {
                debug!("Storage::init: Table created");
            }
            Err(e) => {
                error!("Storage::init: Error creating table: {:?}", e);
                config.active = false;
                pool = None;
                return pool;
            }
        }

        match Self::check_column_exists(&pool.clone().unwrap(), "indra_events", "seq_no").await {
            Ok(exists) => {
                if !exists {
                    match Self::add_seq_no_column(&pool.clone().unwrap(), sq_no).await {
                        Ok(_) => {
                            warn!("Storage::init: New Column seq_no added and initialized with sequential values");
                        }
                        Err(e) => {
                            error!("Storage::init: Error adding column seq_no: {:?}", e);
                            config.active = false;
                            pool = None;
                            return pool;
                        }
                    }
                }
            }
            Err(e) => {
                error!("Storage::init: Error checking column seq_no: {:?}", e);
                config.active = false;
                pool = None;
                return pool;
            }
        }

        match Self::check_column_exists(&pool.clone().unwrap(), "indra_events", "parent_uuid4")
            .await
        {
            Ok(exists) => {
                if !exists {
                    let add_column_query = "ALTER TABLE indra_events ADD COLUMN parent_uuid4 UUID";
                    match sqlx::query(add_column_query)
                        .execute(&pool.clone().unwrap())
                        .await
                    {
                        Ok(_) => {
                            warn!("Storage::init: New Column parent_uuid4 added");
                        }
                        Err(e) => {
                            error!("Storage::init: Error adding column parent_uuid4: {:?}", e);
                            config.active = false;
                            pool = None;
                            return pool;
                        }
                    }
                }
            }
            Err(e) => {
                error!("Storage::init: Error checking column parent_uui4: {:?}", e);
                config.active = false;
                pool = None;
                return pool;
            }
        }

        let q_res2 = sqlx::query(
        r#"
                    CREATE INDEX IF NOT EXISTS indra_events_domain ON indra_events (domain);
                    CREATE INDEX IF NOT EXISTS indra_events_from_id ON indra_events (to_scope);
                    CREATE INDEX IF NOT EXISTS indra_events_time_start ON indra_events (time_jd_start);
                    CREATE INDEX IF NOT EXISTS indra_events_data_type ON indra_events (data_type);
                    CREATE INDEX IF NOT EXISTS indra_events_time_end ON indra_events (time_jd_end);
                    CREATE INDEX IF NOT EXISTS indra_events_seq_no ON indra_events (seq_no);
                    CREATE INDEX IF NOT EXISTS indra_events_uuid4 ON indra_events (uuid4);
                    CREATE INDEX IF NOT EXISTS indra_events_parent_uuid4 ON indra_events (parent_uuid4);
                    "#,
    )
    .execute(&pool.clone().unwrap())
    .await;
        match q_res2 {
            Ok(_) => {
                debug!("Storage::init: Indices created");
            }
            Err(e) => {
                error!("Storage::init: Error creating indices: {:?}", e);
                config.active = false;
                pool = None;
            }
        }
        if pool.is_none() {
            return pool;
        }
        pool
    }

    fn is_persistent(persistent_domains: Vec<String>, domain: String) -> bool {
        let mut is_persistent = false;
        for per_dom in persistent_domains.iter() {
            if IndraEvent::mqcmp(domain.as_str(), per_dom.as_str()) {
                is_persistent = true;
                break;
            }
        }
        is_persistent
    }
    fn is_volatile(volatile_domains: Vec<(String, i32)>, domain: String) -> bool {
        let mut is_volatile = false;
        for vol_dom_dur in volatile_domains.iter() {
            let vol_dom = vol_dom_dur.0.clone();
            if IndraEvent::mqcmp(domain.as_str(), vol_dom.as_str()) {
                is_volatile = true;
                break;
            }
        }
        is_volatile
    }
}

impl AsyncIndraTask for Storage {
    async fn async_receiver(mut self, sender: async_channel::Sender<IndraEvent>) {
        if !self.config.active {
            return;
        }
        debug!("IndraTask Storage::sender");
        let pool = self.pool;
        loop {
            let msg = self.receiver.recv().await.unwrap();
            if msg.domain == "$cmd/quit" {
                debug!("Storage: Received quit command, quiting receive-loop.");
                // Write last_state to file as json:
                let last_state_json = serde_json::to_string(&self.last_state).unwrap();
                let db_dir = PathBuf::from(self.config.database_directory.clone());
                let stnam = db_dir.join("last_state.json");
                let mut file = File::create(stnam.clone()).unwrap();
                file.write_all(last_state_json.as_bytes()).unwrap();
                info!(
                    "Storage: Last state written to file: {}: {:?}",
                    stnam.to_string_lossy(),
                    self.last_state
                );

                if self.config.active {
                    let _ret = &pool.unwrap().close().await;
                    info!("Storage: Database connection closed.");
                    self.config.active = false;
                }
                break;
            } else if msg.domain.starts_with("$trx/db/") {
                // Random-sampling: SELECT * FROM (SELECT * FROM mytable ORDER BY RANDOM() LIMIT 1000) ORDER BY time;
                if msg.domain == "$trx/db/req/history" {
                    let req_res: Result<IndraHistoryRequest, serde_json::Error> =
                        serde_json::from_str(msg.data.as_str());
                    if req_res.is_err() {
                        error!(
                            "Storage: Error parsing db/req/history command from {}, {:?}: {:?}",
                            msg.from_id, msg.data, req_res
                        );
                        // XXX reply with error
                        continue;
                    }
                    let req: IndraHistoryRequest = req_res.unwrap();
                    info!(
                        "Storage: Received db/req/history command from {} search for: {:?}",
                        msg.from_id, req
                    );
                    match req.mode {
                        IndraHistoryRequestMode::Sample => {}
                        IndraHistoryRequestMode::Single => {
                            error!("Storage: Received db/req/history command from {} with unsupported mode: {:?}", msg.from_id, req.mode);
                            continue;
                        }
                        IndraHistoryRequestMode::Interval => {
                            error!("Storage: Received db/req/history command from {} with unsupported mode: {:?}", msg.from_id, req.mode);
                            continue;
                        }
                    }
                    let ut_start = Utc::now();
                    let pool = pool.clone().unwrap();
                    // XXX Support for differrent data_types and HistoryRequestModes
                    let eq1 = match req.domain.contains('%') {
                        true => "LIKE",
                        false => "=",
                    };
                    let eq2 = match req.data_type.contains('%') {
                        true => "LIKE",
                        false => "=",
                    };
                    let mut sql_cmd_str = format!("SELECT id, time_jd_start, data FROM (SELECT * FROM indra_events WHERE domain {} ? AND data_type {} ?", eq1, eq2);
                    // AND time_jd_start >= ? AND time_jd_start <= ? ORDER BY RANDOM() LIMIT ?) ORDER BY time_jd_start ASC
                    if req.time_jd_start.is_some() {
                        sql_cmd_str.push_str(" AND time_jd_start >= ?");
                    }
                    if req.time_jd_end.is_some() {
                        sql_cmd_str.push_str(" AND time_jd_start <= ?");
                    }
                    if req.limit.is_some() {
                        sql_cmd_str.push_str(" ORDER BY RANDOM() LIMIT ?");
                    }
                    sql_cmd_str.push_str(") ORDER BY time_jd_start ASC");
                    let sql_cmd = sql_cmd_str.as_str();
                    let rows_res = sqlx::query_as(sql_cmd)
                        .bind(req.domain.to_string())
                        .bind(req.data_type.to_string());
                    let rr2 = match req.time_jd_start {
                        Some(t) => rows_res.bind(t),
                        None => rows_res,
                    };
                    let rr3 = match req.time_jd_end {
                        Some(t) => rr2.bind(t),
                        None => rr2,
                    };
                    let rr4 = match req.limit {
                        Some(t) => rr3.bind(t),
                        None => rr3,
                    };
                    let rr5 = rr4.fetch_all(&pool).await;
                    let rows: Vec<(i64, f64, String)> = match rr5 {
                        Ok(rows) => rows,
                        Err(e) => {
                            error!("Storage: Error executing query on database: {:?}", e);
                            continue;
                        }
                    };
                    let res: Vec<(f64, f64)> = rows
                        .iter()
                        .map(|row| {
                            let time_jd_start: f64 = row.1;
                            let data_f64_res = row.2.parse::<f64>();
                            if data_f64_res.is_ok() {
                                #[allow(clippy::unnecessary_unwrap)]
                                let data_f64: f64 = data_f64_res.unwrap();
                                (time_jd_start, data_f64)
                            } else {
                                // insert NaN for invalid data:
                                warn!("Storage: Invalid f64 value data in row: {:?}", row);
                                let data_f64: f64 = std::f64::NAN;
                                (time_jd_start, data_f64)
                            }
                        })
                        .filter(|row| !row.1.is_nan())
                        .collect();
                    info!(
                        "Found {} items out of raw {} for {}",
                        res.len(),
                        rows.len(),
                        msg.domain
                    );
                    let ut_end = Utc::now();
                    let rmsg = IndraEvent {
                        domain: msg.from_id.clone(), // .replace("$trx/db/req", "$trx/db/reply"),
                        from_id: self.config.name.clone(),
                        uuid4: msg.uuid4.clone(),
                        parent_uuid4: None,
                        seq_no: None,
                        to_scope: req.domain.clone(),
                        time_jd_start: IndraEvent::datetime_to_julian(ut_start),
                        data_type: "vector/tuple/jd/float".to_string(),
                        data: serde_json::to_string(&res).unwrap(),
                        auth_hash: Default::default(),
                        time_jd_end: Some(IndraEvent::datetime_to_julian(ut_end)),
                    };
                    debug!("Sending: {}->{}", rmsg.from_id, rmsg.domain);
                    if sender.send(rmsg.clone()).await.is_err() {
                        error!(
                            "Storage: Error sending reply-message to channel {}",
                            rmsg.domain
                        );
                    }
                    continue;
                }
                if msg.domain.starts_with("$trx/db/req/uniquedomains") {
                    let req_res: Result<IndraUniqueDomainsRequest, serde_json::Error> =
                        serde_json::from_str(msg.data.as_str());
                    if req_res.is_err() {
                        error!(
                            "Storage: Error parsing db/req/uniquedomains command from {}, {:?}: {:?}",
                            msg.from_id, msg.data, req_res
                        );
                        // XXX reply with error
                        continue;
                    }
                    let req: IndraUniqueDomainsRequest = req_res.unwrap();
                    info!(
                        "Storage: Received db/req/uniquedomains command from {} search for: {:?}",
                        msg.from_id, req
                    );

                    //let rows: Vec<(String)>;
                    let ut_start = Utc::now();
                    let pool = pool.clone().unwrap();
                    let mut sql_cmd = "SELECT DISTINCT domain FROM indra_events".to_string();
                    //  WHERE domain LIKE ? AND data_type LIKE ?;
                    if req.domain.is_some() {
                        sql_cmd.push_str(" WHERE domain LIKE ?");
                        if req.data_type.is_some() {
                            sql_cmd.push_str(" AND data_type LIKE ?");
                        }
                    } else if req.data_type.is_some() {
                        sql_cmd.push_str(" WHERE data_type LIKE ?");
                    };

                    let rows = sqlx::query(&sql_cmd);
                    let rr2 = match req.domain.is_some() {
                        true => rows.bind(req.domain.unwrap_or("%".to_string())),
                        false => rows,
                    };
                    let rr3 = match req.data_type.is_some() {
                        true => rr2.bind(req.data_type.unwrap_or("%".to_string())),
                        false => rr2,
                    };
                    //    .bind(req.domain.unwrap_or("%".to_string()).to_string())
                    //    .bind(req.data_type.unwrap_or("%".to_string()).to_string())
                    let rr4: Vec<String> = rr3
                        .fetch_all(&pool)
                        .await
                        .unwrap()
                        .iter()
                        .map(|rowi| rowi.try_get(0).unwrap())
                        .collect();
                    let ut_end = Utc::now();
                    let rmsg = IndraEvent {
                        domain: msg.from_id.clone().replace("$trx/db/req", "$/trx/db/reply"),
                        from_id: self.config.name.clone(),
                        uuid4: msg.uuid4.clone(),
                        parent_uuid4: None,
                        seq_no: None,
                        to_scope: "".to_string(),
                        time_jd_start: IndraEvent::datetime_to_julian(ut_start),
                        data_type: "vector/string/uniquedomains".to_string(),
                        data: serde_json::to_string(&rr4).unwrap(),
                        auth_hash: Default::default(),
                        time_jd_end: Some(IndraEvent::datetime_to_julian(ut_end)),
                    };
                    info!("Sending domain-list: {}->{}", rmsg.from_id, rmsg.domain);
                    if sender.send(rmsg.clone()).await.is_err() {
                        error!(
                            "Storage: Error sending reply-message to channel {}",
                            rmsg.domain
                        );
                    }
                    continue;
                }
                // Get last value for a given domain
                if msg.domain.starts_with("$trx/db/req/last") {
                    let req_domain = msg.data.clone();
                    // Read the last value (highest jd_start_time) for a given domain into struct IndraEvent:
                    let pool = pool.clone().unwrap();
                    let q_res3 = sqlx::query(
                        r#"
                                SELECT id, domain, from_id, uuid4, parent_uuid4, seq_no, to_scope, time_jd_start, data_type, data, auth_hash, time_jd_end
                                FROM indra_events
                                WHERE domain = ?
                                ORDER BY time_jd_start DESC
                                LIMIT 1
                                "#,
                    )
                    .bind(req_domain)
                    .fetch_one(&pool)
                    .await;

                    let mut rep_msg = IndraEvent {
                        domain: msg.from_id.clone().replace("$trx/db/req", "$/trx/db/reply"),
                        from_id: self.config.name.clone(),
                        uuid4: msg.uuid4.clone(),
                        parent_uuid4: None,
                        seq_no: None,
                        to_scope: "".to_string(),
                        time_jd_start: IndraEvent::datetime_to_julian(Utc::now()),
                        data_type: "".to_string(),
                        data: "".to_string(),
                        auth_hash: Default::default(),
                        time_jd_end: Some(IndraEvent::datetime_to_julian(Utc::now())),
                    };

                    let (last_type, last_ie) = match q_res3 {
                        Ok(row) => (
                            "json/indraevent".to_string(),
                            IndraEvent {
                                domain: row.try_get(1).unwrap(),
                                from_id: row.try_get(2).unwrap(),
                                uuid4: row.try_get(3).unwrap(),
                                parent_uuid4: row.try_get(4).unwrap(),
                                seq_no: row.try_get(5).unwrap(),
                                to_scope: row.try_get(6).unwrap(),
                                time_jd_start: row.try_get(7).unwrap(),
                                data_type: row.try_get(8).unwrap(),
                                data: row.try_get(9).unwrap(),
                                auth_hash: row.try_get(10).unwrap(),
                                time_jd_end: row.try_get(11).unwrap(),
                            },
                        ),
                        Err(_) => ("error/notfound".to_string(), IndraEvent::new()),
                    };
                    rep_msg.data_type = last_type.to_string();
                    rep_msg.data = serde_json::to_string(&last_ie).unwrap();

                    info!(
                        "Sending last value: {}->{}",
                        rep_msg.from_id, rep_msg.domain
                    );
                    if sender.send(rep_msg.clone()).await.is_err() {
                        error!(
                            "Storage: Error sending reply-message to channel {}",
                            rep_msg.domain
                        );
                    }

                    continue;
                }
                warn!("Storage: Received unknown command: {:?}", msg.domain);
                continue;
            }
            if Storage::is_persistent(
                self.config.persistent_domains.clone(),
                msg.clone().domain.clone(),
            ) {
                let mut msg = msg.clone();
                let domain = msg.domain.clone();
                let data_str = msg.data.clone();
                if self.config.active {
                    // ignore Ws* domains
                    debug!("Storage::sender: {:?}", msg);
                    // Insert a new record into the table
                    // XXX, check if data_type and data match!
                    self.last_state.last_seq_no += 1;
                    msg.seq_no = Some(self.last_state.last_seq_no);
                    let rows_affected = sqlx::query(
                            r#"
                                INSERT INTO indra_events (domain, from_id, uuid4, parent_uuid4, seq_no, to_scope, time_jd_start, data_type, data, auth_hash, time_jd_end)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                "#,
                        )
                        .bind(domain)
                        .bind(msg.from_id)
                        .bind(msg.uuid4)
                        .bind(msg.parent_uuid4)
                        .bind(msg.seq_no)
                        .bind(msg.to_scope)
                        .bind(msg.time_jd_start)
                        .bind(msg.data_type)
                        .bind(data_str)
                        .bind(msg.auth_hash)
                        .bind(msg.time_jd_end)
                        .execute(&pool.clone().unwrap())
                        .await.unwrap()
                        .rows_affected();

                    debug!("Inserted {} row(s)", rows_affected);
                }
            }
            if Storage::is_volatile(
                self.config.volatile_domains.clone(),
                msg.clone().domain.clone(),
            ) {
                error!(
                    "Storage::sender: Received forecast domain, NOT IMPLEMENTED: {:?}",
                    msg.clone().domain
                );
            } else {
                warn!(
                    "Storage::sender: Received unknown domain: {:?}",
                    msg.clone().domain
                );
            }
        }
    }

    async fn async_sender(self, _sender: async_channel::Sender<IndraEvent>) {
        loop {
            let _dd: IndraEvent = IndraEvent::new();
            async_std::task::sleep(Duration::from_millis(1000)).await;
            if self.config.active {
                //sender.send(dd).await.unwrap();
            }
        }
    }
}