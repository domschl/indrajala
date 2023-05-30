use crate::IndraEvent;
use std::time::Duration;

use crate::indra_config::SignalConfig; //, IndraTaskConfig};
use crate::{AsyncTaskReceiver, AsyncTaskSender}; // , IndraTask} //, TaskInit};

//use env_logger::Env;
//use log::{debug, error, info, warn};
use log::{debug, info};

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
    async fn async_receiver(self, _sender: async_channel::Sender<IndraEvent>) {
        debug!("IndraTask Signal::sender");
        loop {
            let msg = self.receiver.recv().await.unwrap();

            if msg.domain == "$cmd/quit" {
                debug!("in_async_signal: Received quit command, quiting receive-loop.");
                self.destruct().await;
                break;
            }
            if self.config.active {
                debug!("Signal::sender: {:?}", msg);
            }
        }
    }
}

impl Signal {
    async fn destruct(self) {
        info!("Exit in {} milli seconds...", self.config.shutdown_delay_ms);
        async_std::task::sleep(Duration::from_millis(self.config.shutdown_delay_ms)).await;
        info!("Process Exit.");
        std::process::exit(0);
    }
}

impl Signal {
    async fn handle_signals(
        mut self,
        mut signals: Signals,
        sender: async_channel::Sender<IndraEvent>,
    ) {
        debug!("Signal handler started");
        while let Some(signal) = signals.next().await {
            info!("SIGNAL EVENT");
            match signal {
                SIGHUP => {
                    info!("SIGHUP received");
                    // Reload configuration
                    // Reopen the log file
                }
                SIGTERM | SIGINT | SIGQUIT => {
                    // Shutdown the system;
                    info!("SIGTERM | SIGINT | SIGQUIT received");
                    self.config.active = false;
                    let a = "$cmd/quit".to_string();
                    let b = "".to_string();
                    let mut dd: IndraEvent;
                    dd = IndraEvent::new();
                    dd.domain = a.to_string();
                    dd.from_id = self.config.name.to_string();
                    dd.data = b;
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
            // XXX remove this loop
            async_std::task::sleep(Duration::from_millis(100)).await;
            if !self.config.active {
                debug!("Signal handler not active, quitting sender-loop.");
                break;
            }
        }

        // Terminate the signal stream.  XXX remove.
        handle.close();
        signals_task.await;

        //Ok(())
    }
}
