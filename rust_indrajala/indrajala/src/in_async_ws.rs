use crate::indra_config::WsConfig;
use crate::IndraEvent;
use crate::{AsyncTaskReceiver, AsyncTaskSender};

use std::io;
use std::path::{Path, PathBuf};
use std::{
    collections::HashMap,
    fs::File,
    io::BufReader,
    net::SocketAddr,
    sync::{Arc, RwLock},
};

use async_channel;
use async_std::net::{TcpListener, TcpStream};
use async_std::task;
//use async_tungstenite::tungstenite::protocol::Message;
use async_tungstenite::{async_std::connect_async, tungstenite::Message};

// use tide_rustls::TlsListener;

use futures::prelude::*;
use futures::{
    channel::mpsc::{unbounded, UnboundedSender},
    future, pin_mut,
};

use log::{debug, error, info, warn};

use rustls::internal::pemfile::{certs, pkcs8_private_keys}; // rsa_private_keys
use rustls::NoClientAuth;
use rustls::{Certificate, PrivateKey, ServerConfig};
use rustls_pemfile::{read_one, Item};

use async_tls::TlsAcceptor;

use async_std::stream::StreamExt;
//use futures_lite::io::AsyncWriteExt;
use std::net::ToSocketAddrs;
//use structopt::StructOpt;

type Tx = UnboundedSender<Message>;
type PeerMap = Arc<RwLock<HashMap<SocketAddr, Tx>>>;

#[derive(Clone)]
pub struct Ws {
    pub config: WsConfig,
    pub connections: PeerMap,
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
            connections: PeerMap::new(RwLock::new(HashMap::new())),
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
            let wmsg = Message::Text(msg_text);
            let conns = self.connections.clone();
            let peers = conns.read().unwrap().clone();
            /*
            for recp in peers.iter().map(|(_, ws_sink)| ws_sink) {
                recp.unbounded_send(wmsg.clone()).unwrap();
            }
            */
            debug!(
                "Ws: Sending msg {}->{} to {} peers.",
                msg.from_id,
                msg.domain,
                peers.len()
            );
            for recp_tuple in peers.iter() {
                let (addr, ws_sink) = recp_tuple;
                ws_sink.unbounded_send(wmsg.clone()).unwrap();
                info!(
                    "WS-ROUTE: from: {} to: {} via {}",
                    msg.from_id,
                    msg.domain,
                    addr,
                    //                    msg.data.to_string(),
                );
            }
        }
    }
}

async fn handle_connection(
    peer_map: PeerMap,
    stream: TcpStream,
    addr: SocketAddr,
    sender: async_channel::Sender<IndraEvent>,
    name: String,
) {
    info!("Incoming TCP connection from: {}, I am {}", addr, name);

    let ws_stream = async_tungstenite::accept_async(stream)
        .await
        .expect("Error during the websocket handshake occurred");
    debug!("WebSocket connection established: {}", addr);

    // Insert the write part of this peer to the peer map.
    let (tx, rx) = unbounded();
    //peer_map.lock().unwrap().insert(addr, tx);
    peer_map.write().unwrap().insert(addr, tx.clone());
    let p2 = peer_map.read().unwrap().clone();

    let (outgoing, incoming) = ws_stream.split();
    //let sx = sender.clone();

    let broadcast_incoming = incoming
        // XXX remove close
        .try_filter(move |msg| {
            // Broadcasting a Close message from one client
            // will close the other clients.
            future::ready(!msg.is_close())
        })
        .try_for_each(move |msg| {
            if let Message::Text(text) = msg.clone() {
                //debug!("Received: {}", text);
                let iero_res: Result<IndraEvent, serde_json::Error> = serde_json::from_str(&text);
                let mut iero: IndraEvent;
                if iero_res.is_err() {
                    warn!(
                        "WS: Received invalid IndraEvent: {}, {}",
                        text,
                        iero_res.err().unwrap()
                    );
                    tx.unbounded_send("error - not a valid IndraEvent".into())
                        .unwrap();
                } else {
                    iero = iero_res.unwrap();
                    task::block_on(async {
                        iero.from_id = format!("{}/{}", name, addr).to_string().clone();
                        if sender.send(iero.clone()).await.is_err() {
                            error!("Ws: Error sending message to channel, assuming shutdown.");
                            return;
                        }
                    });
                    let peers = p2.clone();

                    // We want to broadcast the message to everyone except ourselves.
                    let broadcast_recipients = peers
                        .iter()
                        .filter(|(peer_addr, _)| peer_addr != &&addr)
                        .map(|(_, ws_sink)| ws_sink);

                    for recp in broadcast_recipients {
                        recp.unbounded_send(msg.clone()).unwrap();
                        info!(
                            "WS-PEER-ROUTE: from: {} to: {} to {}", // [{}]",
                            iero.from_id,
                            iero.domain,
                            addr,
                            //iero.data.to_string().truncate(16),
                        );
                    }
                }
            }

            future::ok(())
        });

    let receive_from_others = rx.map(Ok).forward(outgoing);

    pin_mut!(broadcast_incoming, receive_from_others);
    future::select(broadcast_incoming, receive_from_others).await;

    info!("{} disconnected", &addr);
    peer_map.write().unwrap().remove(&addr);
}

fn load_certs(path: &Path) -> io::Result<Vec<Certificate>> {
    Ok(certs(&mut BufReader::new(File::open(path)?))
        .map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "invalid cert"))?
        .into_iter()
        .map(Certificate.into())
        .collect())
}
fn load_keys(path: &Path) -> io::Result<PrivateKey> {
    match read_one(&mut BufReader::new(File::open(path)?)) {
        Ok(Some(Item::RSAKey(data) | Item::PKCS8Key(data))) => Ok(PrivateKey(data)),
        Ok(_) => Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            format!("invalid key in {}", path.display()),
        )),
        Err(e) => Err(io::Error::new(io::ErrorKind::InvalidInput, e)),
    }
}

pub async fn init_websocket_server(
    connections: PeerMap,
    address: String,
    sender: async_channel::Sender<IndraEvent>,
    wsconfig: WsConfig,
) {
    let url = format!("wss://{}", address);

    let certs = load_certs(&Path::new(wsconfig.cert.as_str())).unwrap();
    let mut keys = load_keys(&Path::new(wsconfig.key.as_str())).unwrap();

    // we don't use client authentication
    let mut config = ServerConfig::new(NoClientAuth::new());
    config
        // set this server to use one cert together with the loaded private key
        .set_single_cert(certs, keys) //  .remove(0))
        .map_err(|err| io::Error::new(io::ErrorKind::InvalidInput, err))
        .unwrap();
}
/*
    // let listener = TcpListener::bind(&addr).await.expect("Can't listen");
    let listener = TlsListener::build()
                    .addrs(wsconfig.address.clone())
                    .cert(wsconfig.cert)
                    .key(wsconfig.key);
    info!("Listening on: {}", addr);

    // Let's spawn the handling of each connection in a separate task.
    while let Ok((stream, addr)) = listener.tls_acceptor(acceptor).await {  //.accept().await {
        task::spawn(handle_connection(
            connections.clone(),
            stream,
            addr,
            sender.clone(),
            wsconfig.name.clone(),
        ));
    }
    //Ok(())
}
*/

impl AsyncTaskSender for Ws {
    async fn async_sender(self, _sender: async_channel::Sender<IndraEvent>) {
        if self.config.active == false {
            return;
        }
    }
}
