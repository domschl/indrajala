use crate::IndraEvent;
use std::time::Duration;

use crate::indra_config::SignalConfig; //, IndraTaskConfig};
use crate::{AsyncTaskReceiver, AsyncTaskSender}; // , IndraTask} //, TaskInit};

//use std::io::Error;

use async_std::prelude::*;

use signal_hook::consts::signal::*;
use signal_hook_async_std::Signals;

#[derive(Clone)]
pub struct Signal {
    pub config: SignalConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
    pub sender: async_channel::Sender<IndraEvent>,
}

impl Signal {
    pub fn new(config: SignalConfig) -> Self {
        let s1: async_channel::Sender<IndraEvent>;
        let r1: async_channel::Receiver<IndraEvent>;
        (s1, r1) = async_channel::unbounded();
        Signal {
            config: config.clone(),
            receiver: r1,
            sender: s1,
        }
    }
}

impl AsyncTaskReceiver for Signal {
    async fn async_receiver(self) {
        // println!("IndraTask Signal::sender");
        loop {
            let msg = self.receiver.recv().await.unwrap();

            if msg.domain == "$cmd/quit" {
                println!("in_async_signal: Received quit command, quiting receive-loop.");
                self.destruct().await;
                break;
            }
            if self.config.active {
                //println!("Signal::sender: {:?}", msg);
            }
        }
    }
}

impl Signal {
    async fn destruct(self) {
        println!("Exit in 2 seconds...");
        async_std::task::sleep(Duration::from_millis(2000)).await;
        println!("Exit...");
        std::process::exit(0);
    }
}

impl Signal {
    async fn handle_signals(
        mut self,
        mut signals: Signals,
        sender: async_channel::Sender<IndraEvent>,
    ) {
        println!("Signal handler!");
        while let Some(signal) = signals.next().await {
            println!("SIG EVENT");
            match signal {
                SIGHUP => {
                    println!("SIGHUP!");
                    // Reload configuration
                    // Reopen the log file
                }
                SIGTERM | SIGINT | SIGQUIT => {
                    // Shutdown the system;
                    println!("SIGTERM | SIGINT | SIGQUIT!");
                    self.config.active = false;
                    let a = "$cmd/quit".to_string();
                    let b = "".to_string();
                    let mut dd: IndraEvent;
                    dd = IndraEvent::new();
                    dd.domain = a.to_string();
                    dd.from_instance = self.config.name.to_string();
                    dd.data = serde_json::json!(b);
                    //dd.data = serde_json(b);
                    sender.send(dd).await.unwrap();
                }
                _ => unreachable!(),
            }
        }
    }
}

impl AsyncTaskSender for Signal {
    async fn async_sender(self, sender: async_channel::Sender<IndraEvent>) {
        let signals = Signals::new(&[SIGHUP, SIGTERM, SIGINT, SIGQUIT]).unwrap();
        let handle = signals.handle();

        let signals_task = async_std::task::spawn(self.clone().handle_signals(signals, sender));

        loop {
            async_std::task::sleep(Duration::from_millis(100)).await;
            if !self.config.active {
                println!("XXXX QUIT");
                break;
            }
        }
        println!("Sig close");

        // Terminate the signal stream.
        handle.close();
        signals_task.await;

        //Ok(())
    }
}
