use crate::indra_config::WebConfig;
use crate::AsyncIndraTask;
use crate::IndraEvent;

// use async_channel;
use log::{debug, info, warn};
use std::collections::HashMap;
// use tide;
use tide::http::convert::Deserialize;
use tide_rustls::TlsListener;
use uuid::Uuid;

#[derive(Clone)]
pub struct Web {
    pub config: WebConfig,
    pub receiver: async_channel::Receiver<IndraEvent>,
    pub sender: async_channel::Sender<IndraEvent>,
    pub subs: Vec<String>,
}

impl Web {
    pub fn new(config: WebConfig) -> Self {
        let s1: async_channel::Sender<IndraEvent>;
        let r1: async_channel::Receiver<IndraEvent>;
        (s1, r1) = async_channel::unbounded();
        let web_config = config;
        let subs = vec![format!("{}/#", web_config.name)];

        Web {
            config: web_config,
            receiver: r1,
            sender: s1,
            subs,
        }
    }
}

impl AsyncIndraTask for Web {
    async fn async_receiver(mut self, _sender: async_channel::Sender<IndraEvent>) {
        debug!("IndraTask Web::sender");
        if !self.config.active {
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

    async fn async_sender(self, sender: async_channel::Sender<IndraEvent>) {
        if !self.config.active {
            return;
        }
        let evpath = self.config.url.clone() + "/event";
        let astate = WebState::new(sender.clone(), IndraEvent::new(), HashMap::new());
        let mut app = tide::with_state(astate); //new();
        let mut ie: IndraEvent = IndraEvent::new();
        ie.domain = "web".to_string();
        ie.data = "Indrajala!".to_string();
        app.at(evpath.as_str())
            .post(|mut req: tide::Request<WebState>| async move {
                let mut st = req.state().clone();
                let ie_res: Result<IndraEvent, tide::Error> = req.body_json().await;
                let mut res: tide::Response = tide::Response::new(tide::StatusCode::Ok);
                #[allow(clippy::unnecessary_unwrap)]
                if ie_res.is_err() {
                    res.set_body(format!("bad request: {}", &ie_res.as_ref().err().unwrap()));
                    res.set_status(tide::StatusCode::BadRequest);
                    warn!("bad request {}", ie_res.err().unwrap());
                } else {
                    st.ie = ie_res.unwrap();
                    if !st.ie.domain.starts_with('$') {
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
            .get(|req: tide::Request<WebState>| async move {
                #[derive(Deserialize)]
                struct Query {
                    domain: String,
                }
                let mut st = req.state().clone();
                let q_res: Result<Query, tide::Error> = req.query();
                if q_res.is_err() {
                    return Ok(format!(
                        "bad request: {} {}",
                        req.url(),
                        &q_res.as_ref().err().unwrap()
                    ));
                }
                let q: Query = q_res.unwrap();
                let domain = q.domain;
                info!("url {} domain {}", req.url(), domain);
                let (sender, _receiver) = async_channel::unbounded::<IndraEvent>();
                let uuid = Uuid::new_v4().to_string();
                // db req.
                // wait on receiver.
                st.sessions.insert(uuid, sender);
                Ok(format!("Indrajala! domain={}", domain))
            });
        app.at("/")
            .get(|_| async move { Ok("Indrajala. API endpoints at ./api/v1/event (POST,GET).") });
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

#[derive(Clone)]
struct WebState {
    sender: async_channel::Sender<IndraEvent>,
    ie: IndraEvent,
    sessions: HashMap<String, async_channel::Sender<IndraEvent>>,
}

impl WebState {
    fn new(
        sender: async_channel::Sender<IndraEvent>,
        ie: IndraEvent,
        sessions: HashMap<String, async_channel::Sender<IndraEvent>>,
    ) -> Self {
        WebState {
            sender,
            ie,
            sessions,
        }
    }
}

// Test with:
// curl --cacert ~/Nextcloud/Security/Certs/ca-root.pem  https://localhost:8081/api/v1/event/full -d '{"domain": "test/ok/XXXXXXXXXXXXXXXX", "from_id":"world-wide-web", "uuid4":"ui324234234234", "to_scope":"to-all-my-friend", "time_jd_start":3.13145, "data_type":"test", "data":"lots-of-data", "auth_hash":"XXX", "time_jd_end":3.2342}'