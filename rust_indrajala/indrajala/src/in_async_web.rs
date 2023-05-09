use crate::indra_config::WebConfig;
use crate::IndraEvent;
use crate::{AsyncTaskReceiver, AsyncTaskSender};

//use env_logger::Env;
//use log::{debug, error, info, warn};
use log::{debug, info, warn};

use tide;
use tide_rustls::TlsListener;
use uuid::Uuid;

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
    fn new(sender: async_channel::Sender<IndraEvent>, ie: IndraEvent) -> Self {
        WebState { sender, ie }
    }
}

// Test with:
// curl --cacert ~/Nextcloud/Security/Certs/ca-root.pem  https://localhost:8081/api/v1/event/full -d '{"domain": "test/ok/XXXXXXXXXXXXXXXX", "from_id":"world-wide-web", "uuid4":"ui324234234234", "to_scope":"to-all-my-friend", "time_start":3.13145, "data_type":"test", "data":"lots-of-data", "auth_hash":"XXX", "time_end":3.2342}'
// curl --cacert ~/Nextcloud/Security/Certs/ca-root.pem  https://localhost:8081/api/v1/event/simple -d '{"domain": "test/ok/XXXXXXXXXXXXXXXX", "from_instance":"world-wide-web", "from_uuid4":"ui324234234234", "to_scope":"to-all-my-friend", "time_start":"2023-04-15T11:28:00CET", "data_type":"test", "data":"lots-of-data", "auth_hash":"XXX", "time_end":"never"}'

impl AsyncTaskSender for Web {
    async fn async_sender(self, sender: async_channel::Sender<IndraEvent>) {
        let astate = WebState::new(sender.clone(), IndraEvent::new());
        let mut app = tide::with_state(astate); //new();
        let mut ie: IndraEvent = IndraEvent::new();
        ie.domain = "web".to_string();
        ie.data = serde_json::json!("Indrajala!");
        let evpath = self.config.url.clone() + "/event/full";
        let evpathsimple = self.config.url.clone() + "/event/simple";
        let pt = evpath.as_str();
        let ptsimple = evpathsimple.as_str();
        app.at(pt)
            .post(|mut req: tide::Request<WebState>| async move {
                warn!("POST");
                let st = req.state().clone();
                let ie_res: Result<IndraEvent, tide::Error> = req.body_json().await;
                let mut res: tide::Response = tide::Response::new(tide::StatusCode::Ok);
                let mut ie: IndraEvent;
                if ie_res.is_err() {
                    res.set_body(format!("bad request: {}", ie_res.err().unwrap()));
                    res.set_status(tide::StatusCode::BadRequest);
                    warn!("bad request");
                } else {
                    ie = ie_res.unwrap();
                    if !ie.domain.starts_with("$") {
                        ie.domain = "$event/".to_string() + ie.domain.as_str();
                    }
                    debug!("SENDING POST: {:?}", ie);
                    res.set_body("Ok");
                    res.set_status(tide::StatusCode::Ok);
                    st.sender.send(ie.clone()).await?;
                }
                Ok(res)
            });
        app.at(ptsimple)
            .post(|mut req: tide::Request<WebState>| async move {
                let st = req.state().clone();
                let IndraEvent {
                    domain,
                    from_id: _,
                    uuid4: _,
                    to_scope: _,
                    time_jd_start,
                    data_type: _,
                    data,
                    auth_hash: _,
                    time_jd_end: _,
                } = req.body_json().await.unwrap();
                let ie = {
                    let mut ie = st.ie.clone();
                    ie.domain = domain;
                    ie.from_id = "indrajala/web".to_string();
                    ie.uuid4 = Uuid::new_v4().to_string();
                    ie.to_scope = "#".to_string();
                    ie.time_jd_start = time_jd_start;
                    ie.data_type = "data".to_string();
                    ie.data = data;
                    // ie.auth_hash = "".to_string();
                    // ie.time_jd_end = time_jd_end;
                    ie
                };
                debug!("SENDING POST: {:?}", ie);
                st.sender.send(ie.clone()).await?;
                Ok("Indrajala!".to_string())
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
