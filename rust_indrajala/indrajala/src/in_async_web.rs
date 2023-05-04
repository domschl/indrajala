use crate::indra_config::WebConfig;
use crate::IndraEvent;
use crate::{AsyncTaskReceiver, AsyncTaskSender};
use tide;
use tide_rustls::TlsListener;

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
        Web {
            config: config.clone(),
            receiver: r1,
            sender: s1,
        }
    }
}

impl AsyncTaskReceiver for Web {
    async fn async_receiver(mut self) {
        //println!("IndraTask Web::sender");
        if self.config.active == false {
            return;
        }
        loop {
            let msg = self.receiver.recv().await.unwrap();
            if msg.domain == "$cmd/quit" {
                println!("Web: Received quit command, quiting receive-loop.");
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
// curl --cacert ~/Nextcloud/Security/Certs/ca-root.pem  https://pergamon:8081/api/v1/event/full -d '{"domain": "test/ok/XXXXXXXXXXXXXXXX", "from_instance":"world-wide-web", "from_uuid4":"ui324234234234", "to_scope":"to-all-my-friend", "time_start":"2023-04-15T11:28:00CET", "data_type":"test", "data":"lots-of-data", "auth_hash":"XXX", "time_end":"never"}'

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
                let st = req.state().clone();
                let IndraEvent {
                    version,
                    seq_no,
                    domain,
                    rev_domain,
                    location,
                    from_instance,
                    from_uuid4,
                    to_scope,
                    time_jd_start,
                    data_type,
                    data,
                    auth_hash,
                    time_jd_end,
                } = req.body_json().await.unwrap();
                let ie = {
                    let mut ie = st.ie.clone();
                    ie.version = version;
                    ie.seq_no = seq_no;
                    ie.domain = domain;
                    ie.rev_domain = rev_domain;
                    ie.location = location;
                    ie.from_instance = from_instance;
                    ie.from_uuid4 = from_uuid4;
                    ie.to_scope = to_scope;
                    ie.time_jd_start = time_jd_start;
                    ie.data_type = data_type;
                    ie.data = data;
                    ie.auth_hash = auth_hash;
                    ie.time_jd_end = time_jd_end;
                    ie
                };
                //println!("SENDING POST: {:?}", ie);
                st.sender.send(ie.clone()).await?;
                Ok("Indrajala!".to_string())
            });
        app.at(ptsimple)
            .post(|mut req: tide::Request<WebState>| async move {
                //println!("-------------------POST---------------");
                let st = req.state().clone();
                let IndraEvent {
                    version,
                    seq_no,
                    domain,
                    rev_domain,
                    location,
                    from_instance: _,
                    from_uuid4: _,
                    to_scope: _,
                    time_jd_start,
                    data_type: _,
                    data,
                    auth_hash: _,
                    time_jd_end: _,
                } = req.body_json().await.unwrap();
                //println!("-------------- After post --------------");
                let ie = {
                    let mut ie = st.ie.clone();
                    ie.version = version;
                    ie.seq_no = seq_no;
                    ie.domain = domain;
                    ie.rev_domain = rev_domain;
                    ie.location = location;
                    ie.from_instance = "indrajala/web".to_string();
                    ie.from_uuid4 = "23432234".to_string();
                    ie.to_scope = "#".to_string();
                    ie.time_jd_start = time_jd_start;
                    ie.data_type = "data".to_string();
                    ie.data = data;
                    // ie.auth_hash = "".to_string();
                    // ie.time_jd_end = time_jd_end;
                    ie
                };
                //println!("SENDING POST: {:?}", ie);
                st.sender.send(ie.clone()).await?;
                Ok("Indrajala!".to_string())
            });
        if self.config.ssl {
            app.listen(
                TlsListener::build()
                    .addrs(self.config.address)
                    .cert(self.config.cert)
                    .key(self.config.key),
            )
            .await
            .unwrap();
        } else {
            app.listen(self.config.address).await.unwrap();
        }
    }
}
