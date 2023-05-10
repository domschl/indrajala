use crate::indra_config::WebConfig;
use crate::IndraEvent;
use crate::{AsyncTaskReceiver, AsyncTaskSender};

//use env_logger::Env;
//use log::{debug, error, info, warn};
use log::{debug, info, warn};

use tide;
use tide_rustls::TlsListener;
use tide::http::{convert::Deserialize};
//use tide::Request;
//use uuid::Uuid;

#[derive(Clone)]
pub struct Web {
    pub config: WebConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
    pub sender: async_channel::Sender<IndraEvent>,
}

impl Web {
    pub fn new(config: WebConfig) -> Self {
        let s1: async_channel::Sender<IndraEvent>;
        let r1: async_channel::Receiver<IndraEvent>;
        (s1, r1) = async_channel::unbounded();
        let mut web_config = config.clone();
        let def_addr = format!("{}/#", config.name);
        if !config.out_topics.contains(&def_addr) {
            web_config.out_topics.push(def_addr);
        }
        Web {
            config: web_config.clone(),
            receiver: r1,
            sender: s1,
        }
    }
}

impl AsyncTaskReceiver for Web {
    async fn async_receiver(mut self, _sender: async_channel::Sender<IndraEvent>) {
        debug!("IndraTask Web::sender");
        if self.config.active == false {
            return;
        }
        loop {
            let msg = self.receiver.recv().await.unwrap();
            if msg.domain == "$cmd/quit" {
                debug!("Web: Received quit command, quiting receive-loop.");
                if self.config.active {
                    self.config.active = false;
                }
                break;
            }
        }
    }
}

#[derive(Clone)]
struct WebState {
    sender: async_channel::Sender<IndraEvent>,
    ie: IndraEvent,
}

impl WebState {
    fn new(sender: async_channel::Sender<IndraEvent>, ie: IndraEvent  ) -> Self {
        WebState { sender, ie  }
    }
}

// Test with:
// curl --cacert ~/Nextcloud/Security/Certs/ca-root.pem  https://localhost:8081/api/v1/event/full -d '{"domain": "test/ok/XXXXXXXXXXXXXXXX", "from_id":"world-wide-web", "uuid4":"ui324234234234", "to_scope":"to-all-my-friend", "time_jd_start":3.13145, "data_type":"test", "data":"lots-of-data", "auth_hash":"XXX", "time_jd_end":3.2342}'

impl AsyncTaskSender for Web {
    async fn async_sender(self, sender: async_channel::Sender<IndraEvent>) {
        let evpath = self.config.url.clone() + "/event";
        let astate = WebState::new(sender.clone(), IndraEvent::new());
        let mut app = tide::with_state(astate); //new();
        let mut ie: IndraEvent = IndraEvent::new();
        ie.domain = "web".to_string();
        ie.data = serde_json::json!("Indrajala!");
        app.at(evpath.as_str())
            .post(|mut req: tide::Request<WebState>| async move {
                let mut st = req.state().clone();
                let ie_res: Result<IndraEvent, tide::Error> = req.body_json().await;
                let mut res: tide::Response = tide::Response::new(tide::StatusCode::Ok);
                if ie_res.is_err() {
                    res.set_body(format!("bad request: {}", &ie_res.as_ref().err().unwrap()));
                    res.set_status(tide::StatusCode::BadRequest);
                    warn!("bad request {}", ie_res.err().unwrap());
                } else {
                    st.ie = ie_res.unwrap();
                    if !st.ie.domain.starts_with("$") {
                        st.ie.domain = "$event/".to_string() + st.ie.domain.as_str();
                    }
                    debug!("SENDING POST: {:?}", st.ie);
                    res.set_body("Ok");
                    res.set_status(tide::StatusCode::Ok);
                    st.sender.send(st.ie.clone()).await?;
                }
                Ok(res)
            });
        app.at(evpath.as_str())
            .get(|mut req: tide::Request<WebState>| async move {
                #[derive(Deserialize)]
                struct Query {
                    domain: String,
                }
                let mut st = req.state().clone();
                let q_res: Result<Query, tide::Error> = req.query();
                if q_res.is_err() {
                    return Ok(format!("bad request: {} {}",req.url(), &q_res.as_ref().err().unwrap()).to_string());
                }
                let q: Query = q_res.unwrap();
                let domain = q.domain;
                info!("url {} domain {}", req.url(), domain);
                Ok(format!("Indrajala! domain={}", domain).to_string())
            });
        if self.config.ssl {
            info!("Web: Listening on {} (ssl)", self.config.address);
            app.listen(
                TlsListener::build()
                    .addrs(self.config.address.clone())
                    .cert(self.config.cert)
                    .key(self.config.key),
            )
            .await
            .unwrap();
        } else {
            info!("Web: Listening on {}", self.config.address);
            app.listen(self.config.address).await.unwrap();
        }
        info!("Web: Quitting.");
    }
}
