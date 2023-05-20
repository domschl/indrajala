use crate::indra_config::WsConfig;
use crate::IndraEvent;
use crate::{AsyncTaskReceiver, AsyncTaskSender};

use async_channel;
use futures::stream::SplitSink;
use std::net::SocketAddr;
use std::{
    fs::File,
    io::BufReader,
    sync::{Arc},
    collections::HashMap,
};

use async_std::{
    net::{TcpListener, TcpStream},
    sync::{RwLock},
};

use log::{debug, error, info, warn};

use rustls_pemfile::{certs, pkcs8_private_keys}; //, rsa_private_keys};
use rustls::{ServerConfig};

use async_tls::{
    TlsAcceptor,
    server::TlsStream,
};

use async_tungstenite::{accept_async, WebSocketStream};
use async_tungstenite::tungstenite::protocol::Message;

use futures::sink::{SinkExt};  // for websocket.send()
use futures::StreamExt;

type ActiveConnections = Arc<RwLock<HashMap<SocketAddr, Box<SplitSink<WebSocketStream<TlsStream<TcpStream>>, Message>>>>>;

#[derive(Clone)]
pub struct Ws {
    pub config: WsConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
    pub sender: async_channel::Sender<IndraEvent>,
    pub connections: ActiveConnections,
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
            connections: ActiveConnections::new(RwLock::new(HashMap::new())),
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
            let mut peers = self.connections.write().await; //.unwrap();
            for (_key, value) in peers.iter_mut() {
                let msg = Message::Text(msg_text.clone());
                let mut ws_sink = Box::new(value);
                ws_sink.send(msg).await.unwrap();
            }
            peers.clear();
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

    async fn handle_connection( stream: TlsStream<TcpStream>, name: &str, connections: ActiveConnections , peer_address: SocketAddr, sender: async_channel::Sender<IndraEvent>) -> Result<(), Box<dyn std::error::Error>> {
        let websocket = accept_async(stream).await?;
        info!("Connected session to peer address: {}", peer_address);
        // split websocket into sender and receiver:
        let (ws_sink, mut ws_stream) = websocket.split();
        connections.write().await.insert(peer_address, Box::new(ws_sink));
        while let Some(msg) = ws_stream.next().await {     // websocket.next().await {
            let msg = msg?;
            // check for close message:
            if msg.is_close() {
                info!("Received close message from client: {:?}", msg);
                break;
            }
            info!("Received a message from the client: {:?}", msg);
            let msg_text = msg.to_string();
            let ie: Result<IndraEvent, serde_json::Error> = serde_json::from_str(&msg_text);
            if ie.is_err() {
                warn!("Failed to parse message from client: {:?}", msg_text);
                continue;
            }
            let mut ie = ie.unwrap();
            ie.from_id = format!("{}/{}", name, peer_address.to_string());
            sender.send(ie).await.unwrap();
            //if msg.is_text() || msg.is_binary() {
            //    websocket.send(msg).await?;
            //}
        }
        // remove connection from active
        connections.write().await.remove(&peer_address);
        info!("Disconnected session from peer address: {}", peer_address);
        Ok(())
    }

    async fn accept_loop(connections:ActiveConnections, listener: TcpListener, tls_acceptor: Arc<TlsAcceptor>, name: &str, sender: async_channel::Sender<IndraEvent>) {
        loop {
            let (stream, _) = listener.accept().await.expect("failed to accept");
            let tls_acceptor = tls_acceptor.clone();
            let peer_addr = stream.peer_addr().unwrap();
            info!("Connected to peer address: {}", peer_addr);
            let sx = sender.clone();
            let xname = name.to_string().clone();
            let conns = connections.clone();
            //async_std::task::spawn(async move {
                let stream_res = tls_acceptor.accept(stream).await;
                if stream_res.is_err() {
                    error!("failed to accept TLS stream: {}", stream_res.err().unwrap());
                    return;
                }
                let stream = stream_res.unwrap();
                //let tx, rx = async_channel::unbounded();
                if let Err(e) = handle_connection(stream, xname.as_str(), conns, peer_addr, sx).await {
                    error!("failed to handle connection: {}", e);
                }
            //});
        }
    }

impl AsyncTaskSender for Ws {
    async fn async_sender(self, sender: async_channel::Sender<IndraEvent>) {
        if self.config.active == false {
            return;
        }
        debug!("IndraTask Ws::sender");
    //let data = include_bytes!("voyager.pem");
    //let mut cert_reader = BufReader::new(&data[..]);
    let f = File::open(self.config.cert).unwrap();
    let mut cert_reader = BufReader::new(f);
    let cert_chain = certs(&mut cert_reader)
        .unwrap()
        .iter()
        .map(|v| rustls::Certificate(v.clone()))
        .collect();

    //let dataKey = include_bytes!("voyager.key");
    //let mut key_reader = BufReader::new(&dataKey[..]);
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

    let listener = TcpListener::bind("0.0.0.0:8082").await.unwrap();
    let tls_acceptor = TlsAcceptor::from(Arc::new(ws_config));

    accept_loop(self.connections, listener, Arc::new(tls_acceptor), self.config.name.as_str(), sender).await;

    }
}
