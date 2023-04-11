use crate::IndraEvent;
use std::time::Duration;

pub async fn ding_dong(sender: async_channel::Sender<IndraEvent>) {
    loop {
        let a = "ding".to_string();
        let b = "dong".to_string();
        let mut dd: IndraEvent;
        dd = IndraEvent::new();
        dd.domain = a;
        dd.data = serde_json::json!(b);
        //dd.data = serde_json(b);
        async_std::task::sleep(Duration::from_millis(1000)).await;
        sender.send(dd).await.unwrap();
    }
}
