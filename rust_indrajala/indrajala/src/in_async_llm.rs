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
        if llm_config.active == true {
            info!("Model loaded.");
            let def_addr = format!("{}/#", llm_config.name);
            if !llm_config.out_topics.contains(&def_addr) {
                llm_config.out_topics.push(def_addr);
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

    pub fn get_model(llm_config: &mut LLMConfig) -> Result<Box<dyn llm::Model>, llm::LoadError> {
        info!("Loading LLM model from {}", llm_config.model_path);

        let model_architecture: llm::ModelArchitecture = llm_config.model_arch.parse().unwrap();
        let model_path = Path::new(&llm_config.model_path);
        // check if file exists:
        
        let overrides = serde_json::from_str(llm_config.model_overrides.as_str()).unwrap();

        let model = llm::load_dynamic(
            model_architecture,
            model_path,
            Default::default(),
            overrides,
            LLM::load_progress_callback_logger,
        );
        model
    }

    pub fn send_answer(token: String) -> Result<llm::InferenceFeedback, llm::InferenceError> {
        let answer = token;
        info!("LLM: Answer: {}", answer);
        Ok(llm::InferenceFeedback::Continue)
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
        let model = LLM::get_model(&mut self.config);
        if model.is_err() {
            error!("LLM: Failed to load model: {}", model.err().unwrap());
            return;
        }
        let model = model.unwrap();
        let mut session = model.start_session(Default::default());

        let character_name = "### Assistant";
        let user_name = "### Human";
        let persona = "A chat between a human and an assistant.";
        let history = format!(
            "{character_name}: Hello - How may I help you today?\n\
             {user_name}: What is the capital of France?\n\
             {character_name}:  Paris is the capital of France."
        );
    
        let inference_parameters = llm::InferenceParameters::default();
    
        session
            .feed_prompt(
                model.as_ref(),
                &inference_parameters,
                format!("{persona}\n{history}").as_str(),
                &mut Default::default(),
                llm::feed_prompt_callback(|resp| match resp {
                    llm::InferenceResponse::PromptToken(t)
                    | llm::InferenceResponse::InferredToken(t) => LLM::send_answer(t),
                    _ => Ok(llm::InferenceFeedback::Continue),
                }),
            )
            .expect("Failed to ingest initial prompt.");
    

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
