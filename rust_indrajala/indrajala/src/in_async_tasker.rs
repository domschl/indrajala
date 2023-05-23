use async_channel;
use async_std::{
    io:: {
        ReadExt,
        BufReader,
        BufWriter,
    },
    process:: {
        Command,
        Stdio,
    }, future::IntoFuture,
};

use futures::{
    select, FutureExt,
};

use uuid::Uuid;
use log::{debug, error, info, warn};

use crate::indra_config::TaskerConfig;
use crate::IndraEvent;
use crate::{AsyncTaskReceiver, AsyncTaskSender};

#[derive(Clone)]
pub struct Tasker {
    pub config: TaskerConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
    pub sender: async_channel::Sender<IndraEvent>,
}

impl Tasker {
    pub fn new(config: TaskerConfig) -> Self {
        let s1: async_channel::Sender<IndraEvent>;
        let r1: async_channel::Receiver<IndraEvent>;
        (s1, r1) = async_channel::unbounded();
        let mut tasker_config = config.clone();
        let def_addr = format!("{}/#", config.name);
        if !config.out_topics.contains(&def_addr) {
            tasker_config.out_topics.push(def_addr);
        }
        Tasker {
            config: tasker_config.clone(),
            receiver: r1,
            sender: s1,
        }
    }
}

impl AsyncTaskSender for Tasker {
    async fn async_sender(mut self, sender: async_channel::Sender<IndraEvent>) {
        if !self.config.active {
            debug!("Tasker is not active");
            return;
        }
        let mut cmd_res = Command::new(self.config.cmd.clone())
            .args(self.config.args.clone())
            .stdout(Stdio::piped())
            .stdin(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn();
        if cmd_res.is_err() {
            error!("Tasker: Failed to spawn command: {}, args: {:?}: {}", self.config.cmd, self.config.args, cmd_res.err().unwrap());
            return;
        }
        let mut child = cmd_res.unwrap();
        


        let mut child_stdin = child.stdin.take().expect(format!("Failed to open stdin for {}", self.config.name).as_str());
        let mut child_stdout = child.stdout.take().expect("Failed to open stdout");
        let mut child_stderr = child.stderr.take().expect("Failed to open stderr");

        // get BufReaders for child stdout and stderr
        let mut child_stdout_br = BufReader::new(child_stdout);
        let mut child_stderr_br = BufReader::new(child_stderr);
        // get BufWriter for child stdin
        let mut child_stdin_bw = BufWriter::new(child_stdin);

        let mut child_stdout_c: [u8; 1] = [0];
        let mut child_stderr_c: [u8; 1] = [0];
        let mut child_stdout: String = String::new();
        let mut child_stderr: String = String::new();


        // get futures for reading from child stdout and stderr
        let mut child_stdout_future = child_stdout_br.read_exact(&mut child_stdout_c).fuse();
        let mut child_stderr_future = child_stderr_br.read_exact(&mut child_stderr_c).fuse();
        let mut receive_future = self.receiver.recv().fuse();
        
        loop {
            select! {
                receive_result = receive_future => {
                    if receive_result.is_err() {
                        warn!("Tasker: Failed to receive message: {}", receive_result.err().unwrap());
                        receive_future = self.receiver.recv().fuse();
                        continue;
                    }
                    let msg = receive_result.unwrap();
                    if msg.domain == "$cmd/quit" {
                        info!("Tasker: Received quit command, quiting receive-loop.");
                        self.config.active = false;
                        break;
                    }
                    info!("Tasker: Received message: {}", msg.domain);
                    if self.config.active {
                        info!("Tasker::sender (publisher): {}", msg.domain);
                    }
                    receive_future = self.receiver.recv().fuse();
                },
                child_result = child_stdout_future => {
                    if child_result.is_err() {
                        // warn!("Tasker: Failed to read from child: STD {}", child_result.err().unwrap());
                        child_stdout_future = child_stdout_br.read_exact(&mut child_stdout_c).fuse();
                        continue;
                    }
                    let vc = child_stdout_c;
                    if vc.len() > 0 {
                        if vc[0] == 10 {
                            info!("Tasker: Received from child: {}", child_stdout);
                            child_stdout.clear();
                            continue;
                        } else {
                            child_stdout.push(vc[0] as char);
                        }
                    }
                    child_stdout_future = child_stdout_br.read_exact(&mut child_stdout_c).fuse();
                },
                child_err_result = child_stderr_future => {
                    if child_err_result.is_err() {
                        // warn!("Tasker: Failed to read from child: ERR {}", child_err_result.err().unwrap());
                        child_stderr_future = child_stderr_br.read_exact(&mut child_stderr_c).fuse();
                        continue;
                    }
                    let vc = child_stderr_c;
                    if vc.len() > 0 {
                        if vc[0] == 10 {
                            info!("Tasker: Received from child: {}", child_stderr);
                            child_stderr.clear();
                            continue;
                        } else {
                            child_stderr.push(vc[0] as char);
                        }
                    }
                    child_stderr_future = child_stderr_br.read_exact(&mut child_stderr_c).fuse();
                    // info!("Tasker: Received from child: {}", child_error);
                    // child_error.clear();
                }
            }
            
        }
        let status = child.status().await.unwrap();
        println!("Task exited with status: {}", status);

    }
}

impl AsyncTaskReceiver for Tasker {
    async fn async_receiver(mut self, _sender: async_channel::Sender<IndraEvent>) {
        loop {
            let msg = self.receiver.recv().await.unwrap();
            if msg.domain == "$cmd/quit" {
                debug!("Tasker: Received quit command, quiting receive-loop.");
                self.config.active = false;
                break;
            }
            if self.config.active {
                debug!("Tasker::sender (publisher): {}", msg.domain);
            }
        }
    }
}
