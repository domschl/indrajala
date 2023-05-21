use crate::indra_config::WsConfig;
use crate::IndraEvent;
use crate::{AsyncTaskReceiver, AsyncTaskSender};

use async_channel;
use futures::stream::SplitSink;
use std::net::SocketAddr;
use std::{collections::HashMap, fs::File, io::BufReader, sync::Arc};

use async_std::{
    net::{TcpListener, TcpStream},
    sync::RwLock,
};

use log::{debug, error, info, warn};

use rustls::ServerConfig;
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
    pub wss_connections: ActiveWssConnections,
    pub ws_connections: ActiveWsConnections,
}

impl Ws {
    pub fn new(config: WsConfig) -> Self {
        let s1: async_channel::Sender<IndraEvent>;
        let r1: async_channel::Receiver<IndraEvent>;
        (s1, r1) = async_channel::unbounded();
        let mut ws_config = config.clone();
        let def_addr = format!("{}/#", config.name);
        if !config.out_topics.contains(&def_addr) {
            ws_config.out_topics.push(def_addr);
        }

        Ws {
            config: ws_config.clone(),
            receiver: r1,
            sender: s1,
            wss_connections: ActiveWssConnections::new(RwLock::new(HashMap::new())),
            ws_connections: ActiveWsConnections::new(RwLock::new(HashMap::new())),
        }
    }
}

impl AsyncTaskReceiver for Ws {
    async fn async_receiver(mut self, _sender: async_channel::Sender<IndraEvent>) {
        debug!("IndraTask Ws::receiver");
        loop {
            let msg = self.receiver.recv().await.unwrap();
            if msg.domain == "$cmd/quit" {
                debug!("Ws: Received quit command, quiting receive-loop.");
                if self.config.active {
                    self.config.active = false;
                }
                break;
            }
            let msg_text = serde_json::to_string(&msg).unwrap();
            let mut ws_dead_conns = Vec::new();
            let mut wss_dead_conns = Vec::new();
            if self.config.ssl == true {
                let mut peers = self.wss_connections.write().await;
                for (key, value) in peers.iter_mut() {
                    let msg = Message::Text(msg_text.clone());
                    let ws_sink = Box::new(value);
                    let res = ws_sink.tx.send(msg).await;
                    if res.is_err() {
                        warn!("Error sending message to websocket: {:?}", res);
                        ws_dead_conns.push(key.clone());
                    }
                }
            } else {
                let mut peers = self.ws_connections.write().await;
                for (key, value) in peers.iter_mut() {
                    let msg = Message::Text(msg_text.clone());
                    let ws_sink = Box::new(value);
                    let res = ws_sink.tx.send(msg).await;
                    if res.is_err() {
                        warn!("Error sending message to websocket: {:?}", res);
                        wss_dead_conns.push(key.clone());
                    }
                }
            }
            // Remove dead connections:
            if self.config.ssl == true {
                let mut peers = self.wss_connections.write().await;
                for key in ws_dead_conns.iter() {
                    info!("Removing dead connection: {:?}", key);
                    peers.remove(key);
                }
            } else {
                let mut peers = self.ws_connections.write().await;
                for key in wss_dead_conns.iter() {
                    info!("Removing dead connection: {:?}", key);
                    peers.remove(key);
                }
            }
        }
    }
}

pub async fn init_websocket_server(
    address: String,
    _sender: async_channel::Sender<IndraEvent>,
    _wsconfig: WsConfig,
) {
    let _url = format!("wss://{}", address);
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
        match msg {
            Message::Text(text) => {
                let mut msg: IndraEvent = serde_json::from_str(&text).unwrap();
                // msg.domain = format!("{}/{}", name, msg.domain);
                msg.from_id = format!("{}/{}", name, peer_address);
                sx.send(msg).await.unwrap();
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
    connections
        .write()
        .await
        .insert(peer_address, wss_connection); // Box::new(ws_sink));
    while let Some(msg) = ws_stream.next().await {
        let msg = msg?;
        match msg {
            Message::Text(text) => {
                let mut msg: IndraEvent = serde_json::from_str(&text).unwrap();
                msg.from_id = format!("{}/{}", name, peer_address.to_string());
                info!("Received a message from the client: {:?}", msg);
                sender.send(msg).await.unwrap();
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
                error!("failed to handle connection: {}", e);
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
                error!("failed to handle connection: {}", e);
            }
        });
    }
}

impl AsyncTaskSender for Ws {
    async fn async_sender(self, sender: async_channel::Sender<IndraEvent>) {
        if self.config.active == false {
            return;
        }
        let addr = self.config.address.as_str();
        if self.config.ssl == true {
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
