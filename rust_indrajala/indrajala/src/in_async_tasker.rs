//use async_channel;
use async_std::process::{Command, Stdio};
use futures::future::FutureExt;
use std::pin::pin;
//use futures::Future;
use futures::select;

use log::{debug, error, info, warn};

use crate::indra_config::TaskerConfig;
use crate::AsyncIndraTask;
use crate::IndraEvent;

#[derive(Clone)]
pub struct Tasker {
    pub config: TaskerConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
    pub sender: async_channel::Sender<IndraEvent>,
    pub subs: Vec<String>,
}

impl Tasker {
    pub fn new(config: TaskerConfig) -> Self {
        let s1: async_channel::Sender<IndraEvent>;
        let r1: async_channel::Receiver<IndraEvent>;
        (s1, r1) = async_channel::unbounded();
        let tasker_config = config;
        let subs = vec![format!("{}/#", tasker_config.name)];

        Tasker {
            config: tasker_config,
            receiver: r1,
            sender: s1,
            subs,
        }
    }
}

impl AsyncIndraTask for Tasker {
    async fn async_sender(self, _sender: async_channel::Sender<IndraEvent>) {
        if !self.config.active {
            debug!("Tasker is not active");
        }
    }

    async fn async_receiver(mut self, _sender: async_channel::Sender<IndraEvent>) {
        if !self.config.active {
            debug!("Tasker is not active");
            return;
        }
        let child = Command::new(self.config.cmd.clone())
            .args(self.config.args.clone())
            .stdout(Stdio::piped())
            .stdin(Stdio::piped())
            //.stderr(Stdio::piped())
            .spawn();
        if child.is_err() {
            error!(
                "Tasker: Failed to spawn {} command: {}, args: {:?}: {}",
                self.config.name,
                self.config.cmd,
                self.config.args,
                child.err().unwrap()
            );
            return;
        }
        info!("Started {}", self.config.name);
        let mut child = child.unwrap();
        let mut child_term_fut = pin!(child.status().fuse());
        let mut msg_fut = self.receiver.recv().fuse();

        loop {
            select!(
                msg = msg_fut => {
                    if msg.is_err() {
                        error!("Tasker: Failed to receive message: {}", msg.err().unwrap());
                        break;
                    }
                    let msg = msg.unwrap();
                    if msg.domain == "$cmd/quit" {
                        debug!("Tasker: Received quit command, quiting receive-loop.");
                        self.config.active = false;
                        let res = child.kill();
                        if res.is_err() {
                            error!("Tasker: Failed to kill child process {}: {}", self.config.name, res.err().unwrap());
                            break;
                        }
                        info!("Tasker: Killed child process {}", self.config.name);
                        // wait for term sig. break;
                    } else {
                        msg_fut = self.receiver.recv().fuse();
                    }
                },
                child_term = child_term_fut => {
                    if child_term.is_err() {
                        error!("Tasker: Failed to get child process status: {}", child_term.err().unwrap());
                        break;
                    }
                    let child_term = child_term.unwrap();
                    if child_term.success() {
                        info!("Tasker: Child process {} terminated successfully", self.config.name);
                    } else {
                        warn!("Tasker: Child process {} terminated: {}", self.config.name, child_term);
                    }
                    break;
                }
            );
        }
        info!("Tasker {}: Receive-loop exited", self.config.name)
    }
}
