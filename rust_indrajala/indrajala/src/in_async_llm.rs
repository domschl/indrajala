//use async_channel;
//use async_std::task;
//use futures::future::FutureExt;
//use futures::select;
// use futures::Future;

use llm::{InferenceParameters, InferenceSessionConfig, ModelKVMemoryType, ModelParameters};
//use chrono::Duration;
//use llm;
use log::{debug, error, info, warn};
//use rand;
use std::convert::Infallible;
use std::path::{Path, PathBuf};
//use std::sync::Arc;

use crate::indra_config::LLMConfig;
use crate::AsyncIndraTask;
use crate::IndraEvent;

// Old general References: https://github.com/rustformers/llm/blob/main/crates/llm/examples/vicuna-chat.rs
// Latest API: https://github.com/rustformers/llm/blob/main/binaries/llm-cli/src/cli_args.rs

#[derive(Clone)]
pub struct Llm {
    pub config: LLMConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
    pub sender: async_channel::Sender<IndraEvent>,
    pub subs: Vec<String>,
}

impl Llm {
    pub fn new(config: LLMConfig) -> Self {
        let s1: async_channel::Sender<IndraEvent>;
        let r1: async_channel::Receiver<IndraEvent>;
        (s1, r1) = async_channel::unbounded();
        let llm_config = config; //.clone();
        if llm_config.active {
            info!("Config loaded.");
        }
        let subs = vec![format!("{}/#", llm_config.name)];

        Llm {
            config: llm_config, //.clone(),
            receiver: r1,
            sender: s1,
            subs,
        }
    }

    pub fn to_tokenizer_source(
        tokenizer_path: Option<PathBuf>,
        tokenizer_repository: Option<&str>,
    ) -> llm::TokenizerSource {
        match (tokenizer_path, tokenizer_repository) {
            (Some(_), Some(_)) => {
                panic!("Cannot specify both --tokenizer-path and --tokenizer-repository");
            }
            (Some(path), None) => llm::TokenizerSource::HuggingFaceTokenizerFile(path), // .to_owned()),
            (None, Some(repo)) => llm::TokenizerSource::HuggingFaceRemote(repo.to_owned()),
            (None, None) => llm::TokenizerSource::Embedded,
        }
    }

    /// A implementation for `load_progress_callback` that outputs to `stdout`.
    pub fn load_progress_callback_logger(progress: llm::LoadProgress) {
        match progress {
            llm::LoadProgress::HyperparametersLoaded => info!("Loaded hyperparameters"),
            llm::LoadProgress::ContextSize { bytes } => {
                info!("ggml ctx size = {:.2} MB", bytes as f64 / (1024.0 * 1024.0))
            }
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

    // macos clippy bug
    // #[allow(clippy::needless_pass_by_ref_mut)]
    pub fn inference_callback(
        self,
        stop_sequence: String,
        buf: &mut String, // This triggers a wrong needless mut warning, seemingly only on macos.
        router_sender: async_channel::Sender<IndraEvent>,
    ) -> impl FnMut(llm::InferenceResponse) -> Result<llm::InferenceFeedback, Infallible> + '_ {
        move |resp| match resp {
            llm::InferenceResponse::InferredToken(t) => {
                let mut reverse_buf = buf.clone();
                reverse_buf.push_str(t.as_str());
                if stop_sequence.as_str().eq(reverse_buf.as_str()) {
                    buf.clear();
                    return Ok(llm::InferenceFeedback::Halt);
                } else if stop_sequence.as_str().starts_with(reverse_buf.as_str()) {
                    buf.push_str(t.as_str());
                    return Ok(llm::InferenceFeedback::Continue);
                }

                if buf.is_empty() {
                    self.clone().send_answer(t, router_sender.clone())
                } else {
                    self.clone().send_answer(reverse_buf, router_sender.clone())
                }
            }
            llm::InferenceResponse::EotToken => Ok(llm::InferenceFeedback::Halt),
            _ => Ok(llm::InferenceFeedback::Continue),
        }
    }

    pub fn get_model(llm_config: LLMConfig) -> Result<Box<dyn llm::Model>, llm::LoadError> {
        info!("Loading Llm model from {}", llm_config.model_path);

        let model_architecture: llm::ModelArchitecture = llm_config.model_arch.parse().unwrap();
        let model_path = Path::new(&llm_config.model_path);
        let tokenizer_path: Option<PathBuf> = llm_config.tokenizer_path.map(PathBuf::from);
        let tokenizer_repo: Option<&str> = llm_config.tokenizer_repo.as_deref();
        // check if file exists:

        //let overrides = serde_json::from_str(llm_config.model_overrides.as_str()).unwrap();
        let vocabulary_source = Llm::to_tokenizer_source(tokenizer_path, tokenizer_repo); // llm::VocabularySource::Model;
        let params = ModelParameters {
            prefer_mmap: llm_config.prefer_mmap.unwrap_or(false),
            context_size: llm_config.context_size.unwrap_or(2048),
            use_gpu: llm_config.use_gpu.unwrap_or(false),
            gpu_layers: llm_config.gpu_layers,
            lora_adapters: llm_config.lora_paths.clone(),
            rope_overrides: None, // XXX TODO: llm_config.rope_overrides,
            ..Default::default()
        };
        //let model =
        llm::load_dynamic(
            Some(model_architecture),
            model_path,
            vocabulary_source,
            params, // Default::default(),
            // overrides,
            Llm::load_progress_callback_logger,
        )
        //model
    }

    pub fn send_answer(
        self,
        token: String,
        router_sender: async_channel::Sender<IndraEvent>,
    ) -> Result<llm::InferenceFeedback, Infallible> {
        let answer = token;
        info!("Llm: Answer: {}", answer);
        let mut ie = IndraEvent::new();
        ie.domain = "CHAT.1/1".to_string();
        ie.from_id = "LLM.1".to_string();
        ie.data_type = "string/chat".to_string();
        ie.data = answer;
        let _ = futures::executor::block_on(router_sender.send(ie));
        Ok(llm::InferenceFeedback::Continue)
    }

    pub async fn infer(
        self,
        llm_config: LLMConfig,
        sender: async_channel::Sender<IndraEvent>,
        receiver: async_channel::Receiver<IndraEvent>,
    ) {
        info!("Llm: Starting Llm in long-running thread");
        let model = Llm::get_model(llm_config.clone());
        if model.is_err() {
            error!("Llm: Failed to load model: {}", model.err().unwrap());
            return;
        }
        let model = model.unwrap();

        let mem_typ = if llm_config.no_float16.unwrap_or(false) {
            ModelKVMemoryType::Float32
        } else {
            ModelKVMemoryType::Float16
        };
        let inference_session_config = InferenceSessionConfig {
            memory_k_type: mem_typ,
            memory_v_type: mem_typ,
            n_threads: llm_config.n_threads.unwrap_or_else(|| num_cpus::get() / 2),
            n_batch: llm_config.n_batch.unwrap_or(8),
        };
        info!("Llm: Starting session.");
        let mut session = model.start_session(inference_session_config);

        let character_name = "### Assistant";
        let user_name = "### Human";
        let persona = "A chat between a human and an assistant.";
        let history = format!(
            "{character_name}: Hello - How may I help you today?\n\
             {user_name}: What is the capital of France?\n\
             {character_name}:  Paris is the capital of France."
        );

        let inference_parameters = InferenceParameters {
            /* XXX ToDo new API port!
            sampler: Arc::new(llm::samplers::TopPTopK {
                top_k: llm_config.top_k.unwrap_or(40),
                top_p: llm_config.top_p.unwrap_or(0.95),
                repeat_penalty: llm_config.repeat_penalty.unwrap_or(1.30),
                temperature: llm_config.temperature.unwrap_or(0.8),
                bias_tokens: llm::TokenBias::new(vec![]),
                repetition_penalty_last_n: llm_config.repetition_penalty_last_n.unwrap_or(64),
            }),
            */
            ..Default::default()
        };
        //llm::InferenceParameters::default();

        info!("Llm: Ingesting initial prompt.");
        if session
            .feed_prompt(
                model.as_ref(),
                //&inference_parameters,
                format!("{persona}\n{history}").as_str(),
                &mut Default::default(),
                llm::feed_prompt_callback(|resp| match resp {
                    llm::InferenceResponse::PromptToken(t)
                    | llm::InferenceResponse::InferredToken(t) => {
                        self.clone().send_answer(t, sender.clone())
                    }
                    _ => Ok(llm::InferenceFeedback::Continue),
                }),
            )
            .is_err()
        {
            error!("Llm: Failed to ingest initial prompt");
            return;
        }
        // .expect("Failed to ingest initial prompt.");
        /*
        if res.is_err() {
            error!(
                "Llm: Failed to ingest initial prompt: {}",
                res.err().unwrap()
            );
            return;
        }
        */
        let mut res = llm::InferenceStats::default(); // .clone();
        let mut buf = String::new();

        // let rec = receiver.clone();
        info!("Llm: Starting inference loop.");
        loop {
            let ie_rcv = receiver.recv().await;
            // get ie from channel:

            let ie = match ie_rcv {
                Ok(ie) => ie,
                Err(e) => {
                    info!("Llm thread: Failed to receive IndraEvent: {}", e);
                    continue;
                }
            };

            warn!("Llm thread: Received IndraEvent: {:?}", ie);

            if ie.domain == "$cmd/quit" {
                info!("Llm thread: Received quit command");
                break;
            }
            let line = ie.data.to_string();
            // let readline = rl.readline(format!("{user_name}: ").as_str());
            //print!("{character_name}:");
            //match readline {
            //    Ok(line) => {
            let mut rng = rand::thread_rng();
            let stats = session
                .infer(
                    model.as_ref(),
                    &mut rng,
                    &llm::InferenceRequest {
                        prompt: format!("{user_name}: {line}\n{character_name}:")
                            .as_str()
                            .into(),
                        parameters: &inference_parameters,
                        play_back_previous_tokens: false,
                        maximum_token_count: None,
                    },
                    &mut Default::default(),
                    self.clone().inference_callback(
                        String::from(user_name),
                        &mut buf,
                        sender.clone(),
                    ),
                )
                .unwrap_or_else(|e| {
                    error!("{e}");
                    Default::default()
                });

            res.feed_prompt_duration = res
                .feed_prompt_duration
                .saturating_add(stats.feed_prompt_duration);
            res.prompt_tokens += stats.prompt_tokens;
            res.predict_duration = res.predict_duration.saturating_add(stats.predict_duration);
            res.predict_tokens += stats.predict_tokens;
        }
        info!("\n\nInference stats:\n{res}");
    }
}

impl AsyncIndraTask for Llm {
    async fn async_sender(self, _sender: async_channel::Sender<IndraEvent>) {
        if !self.config.active {
            debug!("Llm is not active");
        }
    }

    async fn async_receiver(self, sender: async_channel::Sender<IndraEvent>) {
        if !self.config.active {
            debug!("Llm is not active");
            return;
        }
        let llm_config = self.config.clone();
        let _name = llm_config.name.clone();
        let sender = sender.clone();
        let receiver = self.receiver.clone();
        info!("Llm: Starting Llm in async thread");
        // let _tsk = async_std::task::spawn_blocking(async move || {
        let tsk = async_std::task::spawn(async {
            self.infer(llm_config, sender, receiver).await;
        });
        info!("Llm: Started Llm in async thread, sleeping...");
        let _blue = tsk.await;
        info!("LLm: Llm async thread terminated.");
        // Sleep forever:
        // let abrt = false;
        while false {
            // sleep 1 sec
            async_std::task::sleep(core::time::Duration::from_secs(1)).await;
        }
    }

    /*
        let mut msg_fut = self.receiver.recv().fuse();
        loop {
            select!(
                msg = msg_fut => {
                    if msg.is_err() {
                        error!("Llm: Failed to receive message: {}", msg.err().unwrap());
                        break;
                    }
                    let msg = msg.unwrap();
                    if msg.domain == "$cmd/quit" {
                        info!("Llm: Received quit command, quiting receive-loop.");
                        // self.config.active = false;
                    } else {
                        msg_fut = self.receiver.recv().fuse();
                        info!("llm: Received message: {:?} in wrong loop", msg)
                    }
                },
                complete => {
                    info!("Llm: complete received, terminating...");
                    break;
                }
            );
        }

        //let _unused = inf.await;
        let _tt = task::block_on(tsk);
        info!("End long-running thread llm ");
        info!("Llm {}: Receive-loop exited (llm thread running)", name);

    }
    */
}
