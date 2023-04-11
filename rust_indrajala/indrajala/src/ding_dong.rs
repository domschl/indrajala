use crate::Indra;
use std::time::Duration;

pub async fn ding_dong(sender: async_channel::Sender<Indra>) {
    loop {
        let a = "ding".to_string();
        let b = "dong".to_string();
        let dd: Indra = (a, b);
        async_std::task::sleep(Duration::from_millis(1000)).await;
        sender.send(dd).await.unwrap();
    }
}
