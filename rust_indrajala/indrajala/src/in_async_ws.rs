use crate::indra_config::WsConfig;
use crate::AsyncIndraTask;
use crate::IndraEvent;

//use async_channel;
use futures::stream::SplitSink;
use std::net::SocketAddr;
use std::{collections::HashMap, fs::File, io::BufReader, sync::Arc};

use async_std::{
    net::{TcpListener, TcpStream},
    sync::RwLock,
};

use log::{debug, error, info, warn};

use rustls::server::ServerConfig;
use rustls_pemfile::{certs, pkcs8_private_keys}; //, rsa_private_keys};

use async_tls::{server::TlsStream, TlsAcceptor};

use async_tungstenite::tungstenite::protocol::Message;
use async_tungstenite::{accept_async, WebSocketStream};

//use futures::channel::mpsc::UnboundedSender;
use futures::sink::SinkExt; // for websocket.send()
use futures::StreamExt;

pub struct WsConnection {
    pub subs: Vec<String>,
    // pub tx: UnboundedSender<Message>,
    pub tx: Box<SplitSink<WebSocketStream<TcpStream>, Message>>,
}
pub struct WssConnection {
    pub subs: Vec<String>,
    pub tx: Box<SplitSink<WebSocketStream<TlsStream<TcpStream>>, Message>>,
}

// type ActiveWssConnections = Arc<RwLock<HashMap<SocketAddr, Box<SplitSink<WebSocketStream<TlsStream<TcpStream>>, Message>>>>>;
type ActiveWssConnections = Arc<RwLock<HashMap<SocketAddr, WssConnection>>>;
type ActiveWsConnections = Arc<RwLock<HashMap<SocketAddr, WsConnection>>>;

#[derive(Clone)]
pub struct Ws {
    pub config: WsConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
    pub sender: async_channel::Sender<IndraEvent>,
    pub subs: Vec<String>,
    pub wss_connections: ActiveWssConnections,
    pub ws_connections: ActiveWsConnections,
}

impl Ws {
    pub fn new(config: WsConfig) -> Self {
        let s1: async_channel::Sender<IndraEvent>;
        let r1: async_channel::Receiver<IndraEvent>;
        (s1, r1) = async_channel::unbounded();
        let ws_config = config;
        let subs = vec![format!("{}/#", ws_config.name)];

        Ws {
            config: ws_config,
            receiver: r1,
            sender: s1,
            subs,
            wss_connections: ActiveWssConnections::new(RwLock::new(HashMap::new())),
            ws_connections: ActiveWsConnections::new(RwLock::new(HashMap::new())),
        }
    }

    pub fn unsub(
        self,
        unsubs: Vec<String>,
        sender: async_channel::Sender<IndraEvent>,
        from_id: String,
    ) {
        let mut ie = IndraEvent::new();
        ie.domain = "$cmd/unsubs".to_string();
        ie.from_id = from_id;
        ie.uuid4 = uuid::Uuid::new_v4().to_string();
        ie.data_type = "vector/string".to_string();
        ie.data = serde_json::to_string(&unsubs).unwrap();
        sender.try_send(ie).unwrap();
    }
}

impl AsyncIndraTask for Ws {
    async fn async_receiver(self, sender: async_channel::Sender<IndraEvent>) {
        debug!("IndraTask Ws::receiver");
        loop {
            let msg = self.receiver.recv().await.unwrap();
            if msg.domain == "$cmd/quit" {
                debug!("Ws: Received quit command, quiting receive-loop.");
                //if self.config.active {
                // self.config.active = false;
                //}
                break;
            }
            let msg_text = serde_json::to_string(&msg).unwrap();
            let mut ws_dead_conns = Vec::new();
            let mut wss_dead_conns = Vec::new();
            if self.config.ssl {
                let mut peers = self.wss_connections.write().await;
                for (key, value) in peers.iter_mut() {
                    let subs: Vec<String> = value.subs.clone();
                    let mut matched = false;
                    for sub in subs.iter() {
                        if IndraEvent::mqcmp(&msg.domain, sub) {
                            matched = true;
                            break;
                        }
                    }
                    let nn = self.clone().config.name.clone();
                    if msg.domain == *format!("{}/{}", nn, key).to_string() {
                        matched = true;
                        info!(
                            "Matched direct-address websocket connection: {}/{:?}, {}",
                            self.clone().config.clone().name,
                            key,
                            msg.domain
                        );
                    }
                    if !matched {
                        info!(
                            "Skipping websocket connection: {:?}, {:?} {}",
                            key, subs, msg.domain
                        );
                        continue;
                    } else {
                        info!(
                            "Matched websocket connection: {:?}, {:?} {}",
                            key, subs, msg.domain
                        );
                    }
                    let msg = Message::Text(msg_text.clone());
                    let ws_sink = Box::new(value);
                    let res = ws_sink.tx.send(msg).await;
                    if res.is_err() {
                        warn!("Error sending message to websocket: {:?}", res);
                        // ws_dead_conns.push(key.clone());
                        ws_dead_conns.push(*key);
                    }
                }
            } else {
                let mut peers = self.ws_connections.write().await;
                for (key, value) in peers.iter_mut() {
                    let subs: Vec<String> = value.subs.clone();
                    let mut matched = false;
                    for sub in subs.iter() {
                        if IndraEvent::mqcmp(&msg.domain, sub) {
                            matched = true;
                            break;
                        }
                    }
                    if msg.domain == *format!("{}/{}", self.config.name, key).to_string() {
                        matched = true;
                        info!(
                            "Matched direct-address websocket connection: {}/{:?}, {}",
                            self.config.name, key, msg.domain
                        );
                    }
                    if !matched {
                        info!(
                            "Skipping websocket connection: {:?}, {:?} {}",
                            key, subs, msg.domain
                        );
                        continue;
                    } else {
                        info!(
                            "Matched websocket connection: {:?}, {:?} {}",
                            key, subs, msg.domain
                        );
                    }
                    let msg = Message::Text(msg_text.clone());
                    let ws_sink = Box::new(value);
                    let res = ws_sink.tx.send(msg).await;
                    if res.is_err() {
                        warn!("Error sending message to websocket: {:?}", res);
                        //wss_dead_conns.push(key.clone());
                        wss_dead_conns.push(*key);
                    }
                }
            }
            // Remove dead connections:
            if self.config.ssl {
                let mut peers = self.wss_connections.write().await;
                for key in ws_dead_conns.iter() {
                    let from_id = format!("{}/{}", self.config.name, key).to_string();
                    self.clone()
                        .unsub(peers[key].subs.clone(), sender.clone(), from_id);
                    info!("Removing dead connection: {:?}", key);
                    peers.remove(key);
                }
            } else {
                let mut peers = self.ws_connections.write().await;
                for key in wss_dead_conns.iter() {
                    let from_id = format!("{}/{}", self.config.name, key).to_string();
                    info!("Removing dead connection: {:?}", key);
                    self.clone()
                        .unsub(peers[key].subs.clone(), sender.clone(), from_id);
                    peers.remove(key);
                }
            }
        }
    }

    async fn async_sender(self, sender: async_channel::Sender<IndraEvent>) {
        if !self.config.active {
            return;
        }
        let addr = self.config.address.as_str();
        if self.config.ssl {
            debug!("IndraTask Ws::sender: SSL enabled");

            let f = File::open(self.config.cert).unwrap();
            let mut cert_reader = BufReader::new(f);
            let cert_chain = certs(&mut cert_reader)
                .unwrap()
                .iter()
                .map(|v| rustls::Certificate(v.clone()))
                .collect();
            let f = File::open(self.config.key).unwrap();
            let mut key_reader = BufReader::new(f);
            let mut keys = pkcs8_private_keys(&mut key_reader)
                .unwrap()
                .iter()
                .map(|v| rustls::PrivateKey(v.clone()))
                .collect::<Vec<_>>();
            let key = keys.remove(0);

            let ws_config = ServerConfig::builder()
                .with_safe_defaults()
                .with_no_client_auth()
                .with_single_cert(cert_chain, key)
                .expect("bad certificate/key");

            let listener = TcpListener::bind(addr).await.unwrap();
            info!("Ws: Listening on wss://{} (ssl)", addr);
            let tls_acceptor = TlsAcceptor::from(Arc::new(ws_config));

            wss_accept_loop(
                self.wss_connections,
                listener,
                Arc::new(tls_acceptor),
                self.config.name.as_str(),
                sender,
            )
            .await;
        } else {
            debug!("IndraTask Ws::sender: SSL disabled");

            let listener = TcpListener::bind(addr).await.unwrap();
            info!("Ws: Listening on ws://{}", addr);

            ws_accept_loop(
                self.ws_connections,
                listener,
                self.config.name.as_str(),
                sender,
            )
            .await;
        }
    }
}

async fn handle_message(
    msg: Message,
    name: &str,
    peer_address: SocketAddr,
    subs: &mut Vec<String>,
    sx: async_channel::Sender<IndraEvent>,
) {
    match msg {
        Message::Text(text) => {
            let mut msg;
            let msg_res: Result<IndraEvent, serde_json::Error> = serde_json::from_str(&text);
            if msg_res.is_err() {
                warn!("Error parsing message: >{}<, {:?}", text, msg_res);
                return;
            } else {
                msg = msg_res.unwrap();
            }
            match msg.domain.as_str() {
                "$cmd/subs" => {
                    warn!("Received subs command: {:?}", msg);
                    //let mut subs = subs;
                    let new_subs_res: Result<Vec<String>, serde_json::Error> =
                        serde_json::from_str(msg.data.as_str());
                    if new_subs_res.is_ok() {
                        let new_subs = new_subs_res.unwrap();
                        for sub in new_subs.iter() {
                            let ev_sub = if !sub.starts_with("$event/") {
                                // XXX useless hack, tbr.
                                format!("$event/{}", sub)
                            } else {
                                sub.clone()
                            };
                            //if !subs.contains(&ev_sub) {  // XXX: allow dups
                            subs.push(ev_sub.clone());
                            //}
                        }
                        warn!("Subscribing to: {:?} -> {:?}", new_subs, subs);
                        info!("Subscriptions updated: {:?}", subs);
                        let mut ie = msg.clone();
                        ie.from_id = format!("{}/{}", name, peer_address);
                        sx.send(ie).await.unwrap();
                    } else {
                        warn!("Error parsing subs command: {:?}", msg);
                    }
                }
                "$trx/echo" => {
                    let mut ie = msg.clone();
                    ie.from_id = ie.domain.clone();
                    ie.domain = format!("{}/{}", name, peer_address);
                    let jd_now = IndraEvent::datetime_to_julian(chrono::Utc::now());
                    ie.time_jd_end = Some(jd_now);
                    info!(
                        "Received echo command: dt={} {:?}",
                        (ie.time_jd_start - jd_now) * 86400.0,
                        msg
                    );
                    sx.send(ie).await.unwrap();
                }
                "$log/error" => {
                    error!("{}: {:?}", msg.from_id, msg.data);
                }
                "$log/warn" => {
                    warn!("{}: {:?}", msg.from_id, msg.data);
                }
                "$log/info" => {
                    info!("{}: {:?}", msg.from_id, msg.data);
                }
                "$log/debug" => {
                    debug!("{}: {:?}", msg.from_id, msg.data);
                }
                _ => {
                    msg.from_id = format!("{}/{}", name, peer_address);
                    info!("Received message via WS -> Route: {:?}", msg);
                    sx.send(msg).await.unwrap();
                }
            }
        }
        Message::Binary(bin) => {
            warn!("Received binary message: {:?}", bin);
        }
        Message::Ping(ping) => {
            warn!("Received ping message: {:?}", ping);
        }
        Message::Pong(pong) => {
            warn!("Received pong message: {:?}", pong);
        }
        Message::Close(close) => {
            warn!("Received close message: {:?}", close);
        }
        Message::Frame(frame) => {
            warn!("Received frame message: {:?}", frame);
        }
    }
}

async fn ws_handle_connection(
    stream: TcpStream,
    connections: ActiveWsConnections,
    name: &str,
    peer_address: SocketAddr,
    sx: async_channel::Sender<IndraEvent>,
) -> Result<(), Box<dyn std::error::Error>> {
    let websocket = accept_async(stream).await?;
    info!("Connected session to peer address: {}", peer_address);
    // split websocket into sender and receiver:
    let (ws_sink, mut ws_stream) = websocket.split();
    let ws_connection: WsConnection = WsConnection {
        subs: Vec::new(),
        tx: Box::new(ws_sink),
    };
    connections
        .write()
        .await
        .insert(peer_address, ws_connection);
    while let Some(msg) = ws_stream.next().await {
        let msg = msg?;
        let mut subs = connections.write().await[&peer_address].subs.clone();
        handle_message(msg, name, peer_address, &mut subs, sx.clone()).await;
        info!("Current subscriptions: {:?}", subs);
        connections
            .write()
            .await
            .get_mut(&peer_address)
            .unwrap()
            .subs = subs;
    }
    connections.write().await.remove(&peer_address);
    Ok(())
}

async fn wss_handle_connection(
    stream: TlsStream<TcpStream>,
    name: &str,
    connections: ActiveWssConnections,
    peer_address: SocketAddr,
    sender: async_channel::Sender<IndraEvent>,
) -> Result<(), Box<dyn std::error::Error>> {
    let websocket = accept_async(stream).await?;
    info!("Connected session to peer address: {}", peer_address);
    // split websocket into sender and receiver:
    let (ws_sink, mut ws_stream) = websocket.split();
    let wss_connection: WssConnection = WssConnection {
        subs: Vec::new(),
        tx: Box::new(ws_sink),
    };
    //let mut subs = wss_connection.subs.clone();
    connections
        .write()
        .await
        .insert(peer_address, wss_connection); // Box::new(ws_sink));
    while let Some(msg) = ws_stream.next().await {
        let msg = msg?;
        let mut subs = connections.write().await[&peer_address].subs.clone();
        handle_message(msg, name, peer_address, &mut subs, sender.clone()).await;
        info!("Current subscriptions: {:?}", subs);
        connections
            .write()
            .await
            .get_mut(&peer_address)
            .unwrap()
            .subs = subs;
    }
    // remove connection from active
    connections.write().await.remove(&peer_address);
    info!("Disconnected session from peer address: {}", peer_address);
    Ok(())
}

async fn ws_accept_loop(
    connections: ActiveWsConnections,
    listener: TcpListener,
    name: &str,
    sender: async_channel::Sender<IndraEvent>,
) {
    loop {
        let (stream, _) = listener.accept().await.expect("failed to accept (WS)");
        let peer_addr = stream.peer_addr().unwrap();
        info!("Connected to peer address: {}", peer_addr);
        let sx = sender.clone();
        let xname = name.to_string().clone();
        let conns = connections.clone();
        async_std::task::spawn(async move {
            if let Err(e) = ws_handle_connection(stream, conns, xname.as_str(), peer_addr, sx).await
            {
                warn!("failed to handle connection: {}", e);
            }
        });
    }
}

async fn wss_accept_loop(
    connections: ActiveWssConnections,
    listener: TcpListener,
    tls_acceptor: Arc<TlsAcceptor>,
    name: &str,
    sender: async_channel::Sender<IndraEvent>,
) {
    loop {
        let (stream, _) = listener.accept().await.expect("failed to accept (WSS)");
        let tls_acceptor = tls_acceptor.clone();
        let peer_addr = stream.peer_addr().unwrap();
        info!("Connected to peer address: {}", peer_addr);
        let sx = sender.clone();
        let xname = name.to_string().clone();
        let conns = connections.clone();
        async_std::task::spawn(async move {
            let stream_res = tls_acceptor.accept(stream).await;
            if stream_res.is_err() {
                error!("failed to accept TLS stream: {}", stream_res.err().unwrap());
                return;
            }
            let stream = stream_res.unwrap();
            if let Err(e) =
                wss_handle_connection(stream, xname.as_str(), conns, peer_addr, sx).await
            {
                warn!("failed to handle connection: {}", e);
            }
        });
    }
}
