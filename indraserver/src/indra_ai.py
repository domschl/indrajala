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
    def __init__(
        self,
        config_data,
        transport,
        event_queue,
        send_queue,
        zmq_event_queue_port,
        zmq_send_queue_port,
    ):
        super().__init__(
            config_data,
            transport,
            event_queue,
            send_queue,
            zmq_event_queue_port,
            zmq_send_queue_port,
            mode="single",
        )
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
                self.translation_active = False
        elif self.application == "translation":
            # https://huggingface.co/google/madlad400-3b-mt
            if self.engine == "huggingface/accelerate/sentencepiece":
                from transformers import T5ForConditionalGeneration, T5Tokenizer

                model_name = config_data[
                    "model"
                ]  # "jbochi/madlad400-3b-mt" "google/madlad400-3b-mt"
                self.model = T5ForConditionalGeneration.from_pretrained(
                    model_name,
                    device_map="cpu",  # auto crashes multiprocessing pickle, tbr.
                )
                self.tokenizer = T5Tokenizer.from_pretrained(model_name)
                self.subscribe(["$trx/translation"])
                self.log.info(
                    "Subscribed to $trx/translation/#, using huggingface/accelerate/sentencepiece"
                )
                self.sentiment_active = False
                self.translation_active = True
        else:
            self.log.error(f"Unknown application: {self.application}")
            self.sentiment_active = False
            self.translation_active = False

    def outbound_init(self):
        if self.translation_active is True or self.sentiment_active is True:
            self.log.info(f"Indra-AI init ok, {self.application} via {self.engine}")
            return True
        else:
            self.log.error("Indra-AI init failed, no application active")
            return False

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
        self.event_send(rev)

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
            self.event_send(rev)
            self.log.info(f"Sentiment result: {result}, sent to {rev.domain}")
        elif IndraEvent.mqcmp(ev.domain, "$trx/translation") is True:
            if self.translation_active is False:
                self._trx_err(ev, "indra_ai translation not active")
                return
            self.log.info(f"Got translation request: {ev.data}")
            translation_data = json.loads(ev.data)
            req_fields = ["text", "lang_code"]
            for rf in req_fields:
                if rf not in translation_data:
                    self._trx_err(ev, f"Missing required field {rf}")
                    return
            text = f"<2{translation_data['lang_code']}> {translation_data['text']}"
            rev = IndraEvent()
            rev.time_jd_start = IndraEvent.datetime2julian(
                datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
            )
            inputs = self.tokenizer.encode(text, return_tensors="pt")
            result = self.model.generate(
                inputs,
                max_length=80,
            )  # , max_length=40, num_beams=4, early_stopping=True)
            rev.domain = ev.from_id
            rev.from_id = self.name
            rev.uuid4 = ev.uuid4
            rev.to_scope = ev.domain
            rev.time_jd_end = IndraEvent.datetime2julian(
                datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
            )
            rev.data_type = "translation"
            translation = self.tokenizer.decode(result[0], skip_special_tokens=True)
            trans_data = {
                "translation": translation,
                "lang_code": translation_data["lang_code"],
            }
            rev.data = json.dumps(trans_data)
            self.event_send(rev)
            self.log.info(f"Translation result: {rev.data}, sent to {rev.domain}")
        else:
            self.log.info(f"Got something: {ev.domain}, sent by {ev.from_id}, ignored")
