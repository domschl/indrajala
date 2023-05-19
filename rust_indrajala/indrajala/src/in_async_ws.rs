use crate::indra_config::WsConfig;
use crate::IndraEvent;
use crate::{AsyncTaskReceiver, AsyncTaskSender};

use async_channel;
use futures::stream::SplitSink;
use std::net::SocketAddr;
use std::{
    fs::File,
    io::BufReader,
    sync::{Arc, RwLock},
    collections::HashMap,
    //net::{TcpListener},
};

use async_std::{
    net::{TcpListener, TcpStream},
    prelude::*,
    //prelude::StreamExt,
};

use log::{debug, error, info, warn};

use rustls_pemfile::{certs, pkcs8_private_keys, rsa_private_keys};
use rustls::{ServerConfig};

use async_tls::{
    TlsAcceptor,
    server::TlsStream,
};

//use tungstenite;
use async_tungstenite::{accept_async, WebSocketStream, Message};
use futures::sink::{SinkExt};  // for websocket.send()
use futures::StreamExt;

// 
/* 
type PeerMap = Arc<RwLock<HashMap<SocketAddr, Tx>>>;
            let conns = self.connections.clone();
            let peers = conns.read().unwrap().clone();
            for recp_tuple in peers.iter() {
                let (addr, ws_sink) = recp_tuple;
                ws_sink.unbounded_send(wmsg.clone()).unwrap();


    let ws_stream = async_tungstenite::accept_async(raw_stream)
        .await
        .expect("Error during the websocket handshake occurred");
    debug!("WebSocket connection established: {}", addr);

    // Insert the write part of this peer to the peer map.
    let (tx, rx) = unbounded();
    //peer_map.lock().unwrap().insert(addr, tx);
    peer_map.write().unwrap().insert(addr, tx.clone());
    let p2 = peer_map.read().unwrap().clone();
*/
struct ConnDesc{
    websocket: async_tungstenite::WebSocketStream<TlsStream<async_std::net::TcpStream>>,
}
//type ActiveConnections = Arc<RwLock<HashMap<SocketAddr, async_tungstenite::WebSocketStream<TlsStream<async_std::net::TcpStream>>>>>;
type ActiveConnections = Arc<RwLock<HashMap<SocketAddr, SplitSink<WebSocketStream<TlsStream<TcpStream>>>>>>;


#[derive(Clone)]
pub struct Ws {
    pub config: WsConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
    pub sender: async_channel::Sender<IndraEvent>,
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
            //connections: PeerMap::new(Mutex::new(HashMap::new())),
            receiver: r1,
            sender: s1,
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

            // let msg_text = msg.to_json().unwrap();
            let msg_text = serde_json::to_string(&msg).unwrap();


        }
    }
}


pub async fn init_websocket_server(
    address: String,
    sender: async_channel::Sender<IndraEvent>,
    wsconfig: WsConfig,
) {
    let url = format!("wss://{}", address);
}

    async fn handle_connection( stream: TlsStream<TcpStream>, name: &str, connections: ActiveConnections , peer_address: SocketAddr, sender: async_channel::Sender<IndraEvent>) -> Result<(), Box<dyn std::error::Error>> {
        let mut websocket = accept_async(stream).await?;
        info!("Connected session to peer address: {}", peer_address);
        // split websocket into sender and receiver:
        let (mut ws_sink, mut ws_stream) = websocket.split();
        connections.write().unwrap().insert(peer_address, ws_sink);
        while let Some(msg) = websocket.next().await {
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
        info!("Disconnected session from peer address: {}", peer_address);
        Ok(())
    }

    async fn accept_loop(listener: TcpListener, tls_acceptor: Arc<TlsAcceptor>, name: &str, sender: async_channel::Sender<IndraEvent>) {
        loop {
            let (stream, _) = listener.accept().await.expect("failed to accept");
            let tls_acceptor = tls_acceptor.clone();
            let connections: ActiveConnections = Arc::new(RwLock::new(HashMap::new()));
            // get ip address from originator:
            let peer_addr = stream.peer_addr().unwrap();
            info!("Connected to peer address: {}", peer_addr);
            let sx = sender.clone();
            let xname = name.to_string().clone();
            async_std::task::spawn(async move {
                //let peer_addr = stream.peer_addr().unwrap();
                //let xname = name.to_string().clone();
                let stream_res = tls_acceptor.accept(stream).await;
                if stream_res.is_err() {
                    error!("failed to accept TLS stream: {}", stream_res.err().unwrap());
                    return;
                }
                let stream = stream_res.unwrap();
                if let Err(e) = handle_connection(stream, xname.as_str(), connections, peer_addr, sx).await {
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

    let config = ServerConfig::builder()
        .with_safe_defaults()
        .with_no_client_auth()
        .with_single_cert(cert_chain, key)
        .expect("bad certificate/key");

    let listener = TcpListener::bind("0.0.0.0:8082").await.unwrap();
    let tls_acceptor = TlsAcceptor::from(Arc::new(config));
    accept_loop(listener, Arc::new(tls_acceptor), self.config.name.as_str(), sender).await;

    }
}
