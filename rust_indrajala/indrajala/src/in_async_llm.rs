use async_channel;
use futures::future::FutureExt;
//use futures::Future;
use futures::select;

use log::{debug, error, info};
use std::path::Path;

use llm;

use crate::indra_config::LLMConfig;
use crate::IndraEvent;
use crate::{AsyncTaskReceiver, AsyncTaskSender};

#[derive(Clone)]
pub struct LLM {
    pub config: LLMConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
    pub sender: async_channel::Sender<IndraEvent>,
}

impl LLM {
    pub fn new(config: LLMConfig) -> Self {
        let s1: async_channel::Sender<IndraEvent>;
        let r1: async_channel::Receiver<IndraEvent>;
        (s1, r1) = async_channel::unbounded();
        let mut llm_config = config.clone();

        info!("Loading LLM model from {}", config.model_path);

        let model_architecture: llm::ModelArchitecture = config.model_arch.parse().unwrap();
        let model_path = Path::new(&config.model_path);
        // check if file exists:
        if !model_path.exists() {
            error!("Model file {} does not exist", config.model_path);
            llm_config.active = false;
        }
        let overrides = serde_json::from_str(config.model_overrides.as_str()).unwrap();

        let model = llm::load_dynamic(
            model_architecture,
            model_path,
            Default::default(),
            overrides,
            LLM::load_progress_callback_logger,
        );
        if model.is_err() {
            let emsg = model.err().unwrap();
            error!("Failed to load {model_architecture} model from {model_path:?}, {emsg}");
            llm_config.active = false;
        } else {
            let model = model.unwrap();
            if llm_config.active == true {
                info!("Model loaded.");
                let def_addr = format!("{}/#", config.name);
                if !config.out_topics.contains(&def_addr) {
                    llm_config.out_topics.push(def_addr);
                }
            }
        }
        LLM {
            config: llm_config.clone(),
            receiver: r1,
            sender: s1,
        }
    }

    /// A implementation for `load_progress_callback` that outputs to `stdout`.
    pub fn load_progress_callback_logger(progress: llm::LoadProgress) {
        match progress {
            llm::LoadProgress::HyperparametersLoaded => info!("Loaded hyperparameters"),
            llm::LoadProgress::ContextSize { bytes } => info!(
                "ggml ctx size = {:.2} MB",
                bytes as f64 / (1024.0 * 1024.0)
            ),
            llm::LoadProgress::TensorLoaded {
                current_tensor,
                tensor_count,
                ..
            } => {
                let current_tensor = current_tensor + 1;
                if current_tensor % 8 == 0 {
                    debug!("Loaded tensor {current_tensor}/{tensor_count}");
                }
            }
            llm::LoadProgress::Loaded {
                file_size: byte_size,
                tensor_count,
            } => {
                info!("Loading of model complete");
                info!(
                    "Model size = {:.2} MB / num tensors = {}",
                    byte_size as f64 / 1024.0 / 1024.0,
                    tensor_count
                );
            }
            llm::LoadProgress::LoraApplied { name, source } => {
                info!(
                    "Patched tensor {} via LoRA from '{}'",
                    name,
                    source.file_name().unwrap().to_str().unwrap()
                );
            }
        };
    }
}
impl AsyncTaskSender for LLM {
    async fn async_sender(self, _sender: async_channel::Sender<IndraEvent>) {
        if !self.config.active {
            debug!("LLM is not active");
            return;
        }
    }
}

impl AsyncTaskReceiver for LLM {
    async fn async_receiver(mut self, _sender: async_channel::Sender<IndraEvent>) {
        if !self.config.active {
            debug!("LLM is not active");
            return;
        }
        let mut msg_fut = self.receiver.recv().fuse();
        loop {
            select!(
                msg = msg_fut => {
                    if msg.is_err() {
                        error!("LLM: Failed to receive message: {}", msg.err().unwrap());
                        break;
                    }
                    let msg = msg.unwrap();
                    if msg.domain == "$cmd/quit" {
                        debug!("LLM: Received quit command, quiting receive-loop.");
                        self.config.active = false;
                    } else {
                        msg_fut = self.receiver.recv().fuse();
                    }
                },
            );
        }
        info!("LLM {}: Receive-loop exited", self.config.name)
    }
}
