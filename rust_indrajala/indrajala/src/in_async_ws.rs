use crate::indra_config::WsConfig;
use crate::IndraEvent;
use crate::{AsyncTaskReceiver, AsyncTaskSender};
use std::{
    collections::HashMap,
    // io::Error as IoError,
    net::SocketAddr,
    // sync::{Arc, Mutex, RwLock},
    sync::{Arc, RwLock},
};

//use env_logger::Env;
//use log::{debug, error, info, warn};
use log::{debug, error, info, warn};

use futures::prelude::*;
use futures::{
    channel::mpsc::{unbounded, UnboundedSender},
    future, pin_mut,
};

use async_std::net::{TcpListener, TcpStream};
use async_std::task;
use async_tungstenite::tungstenite::protocol::Message;

// use std::time::Duration;

type Tx = UnboundedSender<Message>;
//type PeerMap = Arc<Mutex<HashMap<SocketAddr, Tx>>>;
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
        Ws {
            config: config.clone(),
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

            let msg_text = msg.to_json().unwrap();
            let wmsg = Message::Text(msg_text);
            let conns = self.connections.clone();
            let peers = conns.read().unwrap().clone();
            /*
            for recp in peers.iter().map(|(_, ws_sink)| ws_sink) {
                recp.unbounded_send(wmsg.clone()).unwrap();
            }
            */
            debug!("Ws: Sending msg {}->{} to {} peers.", msg.from_instance, msg.domain, peers.len());
            for recp_tuple in peers.iter() {
                let (addr, ws_sink) = recp_tuple;
                ws_sink.unbounded_send(wmsg.clone()).unwrap();
                info!(
                    "WS-ROUTE: from: {} to: {} via {} [{}]",
                    msg.from_instance,
                    msg.domain,
                    addr,
                    msg.data.to_string()
                );
            }
        }
    }
}

async fn handle_connection(
    peer_map: PeerMap,
    raw_stream: TcpStream,
    addr: SocketAddr,
    sender: async_channel::Sender<IndraEvent>,
    name: String,
) {
    info!("Incoming TCP connection from: {}, I am {}, sender is {:?}", addr, name, sender);

    let ws_stream = async_tungstenite::accept_async(raw_stream)
        .await
        .expect("Error during the websocket handshake occurred");
    debug!("WebSocket connection established: {}", addr);

    // Insert the write part of this peer to the peer map.
    let (tx, rx) = unbounded();
    //peer_map.lock().unwrap().insert(addr, tx);
    peer_map.write().unwrap().insert(addr, tx);
    let p2 = peer_map.read().unwrap().clone();

    let (outgoing, incoming) = ws_stream.split();
    //let sx = sender.clone();

    let broadcast_incoming = incoming
        .try_filter(move |msg| {
            // Broadcasting a Close message from one client
            // will close the other clients.
            future::ready(!msg.is_close())
        })
        .try_for_each(move |msg| {
            if let Message::Text(text) = msg.clone() {
                debug!("Received: {}", text);
                let mut iero = IndraEvent::from_json(&text).unwrap();
                task::block_on(async {
                    iero.from_instance = format!("{}/{}", name, addr).to_string().clone();
                    debug!("Received->Send: {:?}", iero);
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
                        "WS-PEER-ROUTE: from: {} to: {} to {} [{}]",
                        iero.from_instance,
                        iero.domain,
                        addr,
                        iero.data.to_string()
                    );
                }
            }

            future::ok(())
        });

    let receive_from_others = rx.map(Ok).forward(outgoing);

    pin_mut!(broadcast_incoming, receive_from_others);
    future::select(broadcast_incoming, receive_from_others).await;

    warn!("{} disconnected", &addr);
    peer_map.write().unwrap().remove(&addr);
}

pub async fn init_websocket_server(
    connections: PeerMap,
    address: String,
    sender: async_channel::Sender<IndraEvent>,
    name: String,
) {
    let addr = address.as_str();
    let listener = TcpListener::bind(&addr).await.expect("Can't listen");
    info!("Listening on: {}", addr);

    // Let's spawn the handling of each connection in a separate task.
    while let Ok((stream, addr)) = listener.accept().await {
        task::spawn(handle_connection(
            connections.clone(),
            stream,
            addr,
            sender.clone(),
            name.clone(),
        ));
    }
    //Ok(())
}

impl AsyncTaskSender for Ws {
    async fn async_sender(self, _sender: async_channel::Sender<IndraEvent>) {
        if self.config.active == false {
            return;
        }
    }
}
