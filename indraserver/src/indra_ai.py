import os
import sys
import json
import datetime
import uuid

from indralib.indra_event import IndraEvent  # type: ignore
from indralib.indra_time import IndraTime  # type: ignore
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
        print(f"Indra-AI init {config_data["name"]}")
        self.application = config_data["application"]
        self.model_name = config_data["model"]
        self.engine = None
        if "device" in config_data:
            self.device = config_data["device"]
        else:
            self.device = "auto"
        if 'user_id' in config_data:
            self.user_id = config_data['user_id']
            self.session_id = uuid.uuid4().hex
            if 'user_name' in config_data:
                self.user_name = config_data['user_name']
            else:
                self.user_name = None
        else:
            self.user_id = None
            self.user_name = None
            self.session_id = None
        self.log.info(
            f"Indra-AI {config_data["name"]} init: {self.application} {self.model_name} on {self.device}"
        )
        if not os.path.exists(config_data["models_directory"]):
            os.makedirs(config_data["models_directory"])
        models_file = os.path.join(config_data["models_directory"], "models.json")
        self.valid_apps = None
        if os.path.exists(models_file):
            with open(models_file, "r") as f:
                self.valid_apps = json.load(f)
        if self.valid_apps is None:
            self.log.error("No models file found, cannot continue")
            return

        # "translation", "conversational", "forecast"]
        models = None
        for app in self.valid_apps:
            if self.application == app:
                models = self.valid_apps[app]["models"]
                break
        if models is None:
            self.log.error(f"Unknown application: {self.application}")
            self.application = None
            return
        self.model_config = None
        for model in models:
            if self.model_name == model:
                self.model_config = models[model]
                break
        if self.model_config is None:
            self.log.error(f"Unknown model: {self.model_name}")
            self.model = None
            return

        self.engine = self.model_config["engine"]
        model_files = self.model_config["model_files"]
        if "revision" in self.model_config:
            revision = self.model_config["revision"]
        else:
            revision = None

        if self.application == "sentiment":
            self.pipeline = None
            self.model = None
            if self.engine == "huggingface/pipeline/sentiment-analysis":
                from transformers import pipeline

                self.pipeline = pipeline(
                    task="sentiment-analysis",
                    model=model_files,
                    revision=revision,
                    device_map=self.device,
                )
                self.subscribe(["$trx/sentiment"])
                self.log.info(
                    f"Subscribed to $trx/sentiment/#, using {self.model_name} on {self.device}"
                )
            else:
                self.log.error(f"Unknown engine: {self.engine} for sentiment")
                self.application = None
        elif self.application == "translation":
            self.pipeline = None
            self.model = None
            if self.engine == "huggingface/model/translate":
                from transformers import T5ForConditionalGeneration, T5Tokenizer

                self.model = T5ForConditionalGeneration.from_pretrained(
                    model_files,
                    device_map=self.device,  # auto crashes multiprocessing pickle, tbr.
                )
                self.tokenizer = T5Tokenizer.from_pretrained(model_files)
                self.subscribe(["$trx/translation"])
                self.log.info(
                    f"Subscribed to $trx/translation/#, using {self.model_name} on {self.device}"
                )
            else:
                self.log.error(f"Unknown engine: {self.engine} for translation")
                self.application = None
        elif self.application == "conversational":
            self.pipeline = None
            self.model = None
            if self.engine == "huggingface/pipeline/conversational":
                if model_files == "google/gemma-2b-it":
                    from transformers import AutoTokenizer, AutoModelForCausalLM
                    import torch

                    self.tokenizer = AutoTokenizer.from_pretrained("google/gemma-2b-it")
                    self.model = AutoModelForCausalLM.from_pretrained(
                        "google/gemma-2b-it",
                        torch_dtype=torch.bfloat16,
                        device_map=self.device,
                    )
                    self.subscribe(["$trx/conversational"])
                    self.log.info(
                        f"Subscribed to $trx/conversational/#, using huggingface/pipeline/{self.model_name} on {self.device}"
                    )
                else:
                    self.log.error(
                        f"Unknown model: {self.model_name} for conversational"
                    )
            else:
                self.log.error(f"Unknown engine: {self.engine} for conversational")
                self.application = None
        else:
            self.log.error(f"Unknown application: {self.application}")
            self.application = None

    def outbound_init(self):
        if self.application is not None and self.engine is not None:
            self.log.info(f"Indra-AI init ok, {self.application} via {self.engine}")
            if self.user_id is not None:
                ie = IndraEvent()
                ie.domain = f"$interactive/session/start/{self.user_id}"
                ie.from_id = self.name
                ie.data_type = "session_data"
                session_data = {
                    'user': self.user_id,
                    'session_id': self.session_id,
                    'from_id': self.name,
                }
                ie.data = json.dumps(session_data)
                self.event_send(ie)
                self.subscribe(["$event/chat/#"])
                self.log.info(
                    f"Subscribed to $event/chat/# as user {self.user_id} with session {self.session_id}"
                )
            return True
        else:
            if self.application is None:
                self.log.error("Indra-AI init failed, no application specified")
            elif self.engine is None:
                self.log.error(f"Indra-AI init failed, no engine active for application {self.application}")
            return False

    def shutdown(self):
        if self.user_id is not None:
            ie = IndraEvent()
            ie.domain = f"$interactive/session/stop/{self.user_id}"
            ie.from_id = self.name
            ie.data_type = "session_data"
            session_data = {
                'session_id': self.session_id,
            }
            ie.data = json.dumps(session_data)
            self.event_send(ie)
        self.log.info("Shutdown AI complete")

    def _trx_err(self, ev: IndraEvent, err_msg: str):
        self.log.error(err_msg)
        rev = IndraEvent()
        rev.domain = ev.from_id
        rev.from_id = self.name
        rev.uuid4 = ev.uuid4
        rev.to_scope = ev.domain
        rev.time_jd_start = IndraTime.datetime2julian(
            datetime.datetime.now(tz=datetime.timezone.utc)
        )
        rev.time_jd_end = IndraTime.datetime2julian(
            datetime.datetime.now(tz=datetime.timezone.utc)
        )
        rev.data_type = "error/invalid"
        rev.data = json.dumps(err_msg)
        self.event_send(rev)

    def outbound(self, ev: IndraEvent):
        if IndraEvent.mqcmp(ev.domain, "$trx/sentiment") is True:
            if self.application != "sentiment":
                self._trx_err(ev, "indra_ai sentiment analysis not active")
                return
            if self.pipeline is None:
                self._trx_err(
                    ev,
                    "indra_ai sentiment analysis not available, pipeline not initialized",
                )
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
            rev.time_jd_start = IndraTime.datetime2julian(
                datetime.datetime.now(tz=datetime.timezone.utc)
            )
            result = self.pipeline(text)
            rev.domain = ev.from_id
            rev.from_id = self.name
            rev.uuid4 = ev.uuid4
            rev.to_scope = ev.domain
            rev.time_jd_end = IndraTime.datetime2julian(
                datetime.datetime.now(tz=datetime.timezone.utc)
            )
            rev.data_type = "sentiment"
            rev.data = json.dumps(result)
            self.event_send(rev)
            self.log.info(f"Sentiment result: {result}, sent to {rev.domain}")
        elif IndraEvent.mqcmp(ev.domain, "$trx/translation") is True:
            if self.application != "translation":
                self._trx_err(ev, "indra_ai translation not active")
                return
            if self.model is None:
                self._trx_err(
                    ev, "indra_ai translation not available, model not initialized"
                )
                return
            self.log.info(f"Got translation request: {ev.data}")
            translation_data = json.loads(ev.data)
            req_fields = ["text", "lang_code", "max_length"]
            for rf in req_fields:
                if rf not in translation_data:
                    self._trx_err(ev, f"Missing required field {rf}")
                    return
            text = f"<2{translation_data['lang_code']}> {translation_data['text']}"
            rev = IndraEvent()
            rev.time_jd_start = IndraTime.datetime2julian(
                datetime.datetime.now(tz=datetime.timezone.utc)
            )
            inputs = self.tokenizer.encode(text, return_tensors="pt").to(self.device)
            result = self.model.generate(
                inputs,
                max_length=translation_data["max_length"],
            )
            rev.domain = ev.from_id
            rev.from_id = self.name
            rev.uuid4 = ev.uuid4
            rev.to_scope = ev.domain
            rev.time_jd_end = IndraTime.datetime2julian(
                datetime.datetime.now(tz=datetime.timezone.utc)
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
        elif IndraEvent.mqcmp(ev.domain, "$trx/conversational") is True:
            if self.application != "conversational":
                self._trx_err(ev, "indra_ai conversational not active")
                return
            if self.model is None:
                self._trx_err(
                    ev, "indra_ai conversational not available, model not initialized"
                )
                return
            self.log.info(f"Got conversational request: {ev.data}")
            conversation_data = json.loads(ev.data)
            req_fields = ["text", "max_length"]
            for rf in req_fields:
                if rf not in conversation_data:
                    self._trx_err(ev, f"Missing required field {rf}")
                    return
            text = conversation_data["text"]
            max_length = conversation_data["max_length"]
            rev = IndraEvent()
            rev.time_jd_start = IndraTime.datetime2julian(
                datetime.datetime.now(tz=datetime.timezone.utc)
            )
            input_ids = self.tokenizer(text, return_tensors="pt").to(self.device)
            result = self.model.generate(**input_ids, max_length=max_length)
            rev.domain = ev.from_id
            rev.from_id = self.name
            rev.uuid4 = ev.uuid4
            rev.to_scope = ev.domain
            rev.time_jd_end = IndraTime.datetime2julian(
                datetime.datetime.now(tz=datetime.timezone.utc)
            )
            rev.data_type = "chat_reply"
            reply = self.tokenizer.decode(result[0], skip_special_tokens=True)
            conversational_data = {
                "text": reply,
            }
            rev.data = json.dumps(conversational_data)
            self.event_send(rev)
            self.log.info(f"Conversational annotation reply: {rev.data}, sent to {rev.domain}")
        elif IndraEvent.mqcmp(ev.domain, "$event/chat/#") is True:
            try:
                chat_msg = json.loads(ev.data)
            except json.JSONDecodeError:
                self.log.error(
                    f"Failed to decode chat message: {ev.data} from {ev.from_id}"
                )
                return
            req_fields = ["user", "session_id", "message"]
            for field in req_fields:
                if field not in chat_msg:
                    self.log.error(
                        f"Chat message {ev.data} from {ev.from_id} missing required field: {field}"
                    )
                    return
            rev = IndraEvent()
            rev.time_jd_start = IndraTime.datetime2julian(
                datetime.datetime.now(tz=datetime.timezone.utc)
            )
            message = chat_msg["message"]
            input_ids = self.tokenizer(message, return_tensors="pt").to(self.device)
            result = self.model.generate(**input_ids, max_length=256)
            msg_text = self.tokenizer.decode(result[0], skip_special_tokens=True)
            chat_repl_msg = {
                "message": msg_text,
                "user": chat_msg["user"],
                "session_id": chat_msg["session_id"],
            }
            rev.domain = ev.from_id
            rev.from_id = self.name
            rev.uuid4 = ev.uuid4
            rev.to_scope = ev.domain
            rev.time_jd_end = IndraTime.datetime2julian(
                datetime.datetime.now(tz=datetime.timezone.utc)
            )
            rev.data_type = "chat_msg"
            rev.data = json.dumps(chat_repl_msg)
            self.event_send(rev)
            self.log.info(f"Chat: {rev.data}, sent to {rev.domain}")
        else:
            self.log.info(f"Got something: {ev.domain}, sent by {ev.from_id}, ignored")

    def run(self):
        self.launcher()

if __name__ == "__main__":
    print("Starting remote ZMQ indra_ai.py")
    if len(sys.argv) != 3:
        print("Usage: indra_ai.py <main_process_zeromq_port> <json_config_string>")
        sys.exit(1)
    port = int(sys.argv[1])
    try:
        if sys.argv[2][0] == "'" and sys.argv[2][-1] == "'":
            config = json.loads(sys.argv[2][1:-1])
        else:
            config = json.loads(sys.argv[2])
    except Exception as e:
        print("JSON Error: ", e)
        sys.exit(1)

    ipc = IndraProcess(config, "zmq", None, None, port, config["zeromq_port"])
    ipc.run()
