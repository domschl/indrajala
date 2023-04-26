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
    async fn async_sender(self) {
        //println!("IndraTask Ws::sender");
        loop {
            let msg = self.receiver.recv().await.unwrap();
            let msg_text = msg.to_json().unwrap();
            let wmsg = Message::Text(msg_text);
            let conns = self.connections.clone();
            let peers = conns.read().unwrap().clone();
            for recp in peers.iter().map(|(_, ws_sink)| ws_sink) {
                recp.unbounded_send(wmsg.clone()).unwrap();
            }
        }
    }
}

async fn handle_connection(peer_map: PeerMap, raw_stream: TcpStream, addr: SocketAddr) {
    //println!("Incoming TCP connection from: {}", addr);

    let ws_stream = async_tungstenite::accept_async(raw_stream)
        .await
        .expect("Error during the websocket handshake occurred");
    //println!("WebSocket connection established: {}", addr);

    // Insert the write part of this peer to the peer map.
    let (tx, rx) = unbounded();
    //peer_map.lock().unwrap().insert(addr, tx);
    peer_map.write().unwrap().insert(addr, tx);

    let (outgoing, incoming) = ws_stream.split();

    let broadcast_incoming = incoming
        .try_filter(|msg| {
            // Broadcasting a Close message from one client
            // will close the other clients.
            future::ready(!msg.is_close())
        })
        .try_for_each(|msg| {
            //println!(
            //    "Received a message from {}: {}",
            //    addr,
            //    msg.to_text().unwrap()
            //);
            //let peers = peer_map.lock().unwrap();
            let peers = peer_map.read().unwrap();

            // We want to broadcast the message to everyone except ourselves.
            let broadcast_recipients = peers
                .iter()
                .filter(|(peer_addr, _)| peer_addr != &&addr)
                .map(|(_, ws_sink)| ws_sink);

            for recp in broadcast_recipients {
                recp.unbounded_send(msg.clone()).unwrap();
            }

            future::ok(())
        });

    let receive_from_others = rx.map(Ok).forward(outgoing);

    pin_mut!(broadcast_incoming, receive_from_others);
    future::select(broadcast_incoming, receive_from_others).await;

    //println!("{} disconnected", &addr);
    //peer_map.lock().unwrap().remove(&addr);
    peer_map.write().unwrap().remove(&addr);
}

pub async fn init_websocket_server(connections: PeerMap, address: String) {
    let addr = address.as_str();
    let listener = TcpListener::bind(&addr).await.expect("Can't listen");
    //println!("Listening on: {}", addr);

    // Let's spawn the handling of each connection in a separate task.
    while let Ok((stream, addr)) = listener.accept().await {
        task::spawn(handle_connection(connections.clone(), stream, addr));
    }
    //Ok(())
}

impl AsyncTaskSender for Ws {
    async fn async_receiver(self, _sender: async_channel::Sender<IndraEvent>) {
        //println!("IndraTask Ws::receiver");
    }
}
