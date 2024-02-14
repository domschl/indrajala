import json
import datetime

# XXX dev only
import sys
import os

path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "indralib/src",
)
sys.path.append(path)
from indra_event import IndraEvent  # type: ignore

from indra_serverlib import IndraProcessCore


class IndraProcess(IndraProcessCore):
    def __init__(self, event_queue, send_queue, config_data):
        super().__init__(event_queue, send_queue, config_data, mode="single")
        self.application = config_data["application"]
        self.engine = config_data["engine"]
        if self.application == "sentiment":
            if self.engine == "huggingface/pipeline/sentiment-analysis":
                from transformers import pipeline

                model = config_data["model"]
                revision = config_data["revision"]
                self.sentiment_pipeline = pipeline(
                    task="sentiment-analysis", model=model, revision=revision
                )
                self.subscribe(["$trx/sentiment"])
                self.log.info(
                    "Subscribed to $trx/sentiment/#, using huggingface/pipeline/sentiment-analysis"
                )
                self.sentiment_active = True

    def outbound_init(self):
        self.log.info("Indra-AI init complete")
        return True

    def shutdown(self):
        self.log.info("Shutdown AI complete")

    def _trx_err(self, ev: IndraEvent, err_msg: str):
        self.log.error(err_msg)
        rev = IndraEvent()
        rev.domain = ev.from_id
        rev.from_id = self.name
        rev.uuid4 = ev.uuid4
        rev.to_scope = ev.domain
        rev.time_jd_start = IndraEvent.datetime2julian(
            datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        )
        rev.time_jd_end = IndraEvent.datetime2julian(
            datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        )
        rev.data_type = "error/invalid"
        rev.data = json.dumps(err_msg)
        self.event_queue.put(rev)

    def outbound(self, ev: IndraEvent):
        if IndraEvent.mqcmp(ev.domain, "$trx/sentiment") is True:
            if self.sentiment_active is False:
                self._trx_err(ev, "indra_ai sentiment analysis not active")
                return
            self.log.info(f"Got sentiment request: {ev.data}")
            sentiment_data = json.loads(ev.data)
            req_fields = ["text"]
            for rf in req_fields:
                if rf not in sentiment_data:
                    self._trx_err(ev, f"Missing required field {rf}")
                    return
            text = sentiment_data["text"]
            rev = IndraEvent()
            rev.time_jd_start = IndraEvent.datetime2julian(
                datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
            )
            result = self.sentiment_pipeline(text)
            rev.domain = ev.from_id
            rev.from_id = self.name
            rev.uuid4 = ev.uuid4
            rev.to_scope = ev.domain
            rev.time_jd_end = IndraEvent.datetime2julian(
                datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
            )
            rev.data_type = "sentiment"
            rev.data = json.dumps(result)
            self.event_queue.put(rev)
            self.log.info(f"Sentiment result: {result}, sent to {rev.domain}")
        else:
            self.log.info(f"Got something: {ev.domain}, sent by {ev.from_id}, ignored")
