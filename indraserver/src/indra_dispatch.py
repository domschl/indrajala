import json
import datetime
import uuid
import copy

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
        self.chat_sessions = {}
        self.user_sessions = []
        self.async_dist = {}
        self.annotate = config_data["annotate"]
        self.subscribe(
            [
                "$trx/cs/#",
                "$event/chat/#",
                "$interactive/session/#",
                f"{self.name}/annotate/#",
            ]
        )

    def outbound_init(self):
        self.log.info("Indra-dispatch init complete")
        return True

    def shutdown(self):
        self.log.info("Shutdown Dispatch complete")

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
        if IndraEvent.mqcmp(ev.domain, "$interactive/session/#"):
            comps = ev.domain.split("/")
            if len(comps) != 4:
                self.log.error(f"Invalid $interactive/session event: {ev.domain}")
                return
            if comps[2] == "start":
                user = comps[3]
                session_data = json.loads(ev.data)
                req_fields = ["session_id", "user", "from_id"]
                for field in req_fields:
                    if field not in session_data:
                        self.log.error(f"Session start missing required field: {field}")
                        return
                if session_data["user"] != user:
                    self.log.error(
                        f"User domain {user} does not match session user {session_data['user']}, internal error"
                    )
                    return
                self.user_sessions.append(session_data)
                self.log.info(
                    f"User {user} started an interactive session from {session_data['from_id']}"
                )
            elif comps[2] == "end":
                user = comps[3]
                session_data = json.loads(ev.data)
                req_fields = ["session_id", "from_id"]
                for field in req_fields:
                    if field not in session_data:
                        self.log.error(f"Session end missing required field: {field}")
                        return
                session_id = session_data["session_id"]
                found = False
                for user_session in self.user_sessions:
                    if (
                        user_session["session_id"] == session_id
                        and user_session["from_id"] == session_data["from_id"]
                    ):
                        self.log.info(
                            f"User {user} ended an interactive session {session_id} from {user_session['from_id']}"
                        )
                        self.user_sessions.remove(user_session)
                        found = True
                        break
                if found is False:
                    self.log.warning(
                        f"Session {session_id} by {user} at {user_session['from_id']} does not exist"
                    )
                    return
            else:
                self.log.error(f"Invalid $interactive/session event: {ev.domain}")
                return
        elif IndraEvent.mqcmp(ev.domain, "$trx/cs/#"):
            try:
                chat_cmd = json.loads(ev.data)
            except json.JSONDecodeError:
                self.log.error(f"Failed to decode session command: {ev.data}")
                self._trx_err(ev, "Failed to decode session command")
                return
            if "cmd" not in chat_cmd:
                self.log.error(f"Session command missing 'cmd' field: {ev.data}")
                self._trx_err(ev, "Session command missing 'cmd' field")
                return
            if chat_cmd["cmd"] == "new_chat":
                if "participants" not in chat_cmd:
                    self.log.error(
                        f"Session command 'new_session' missing 'participants' field: {ev.data}"
                    )
                    self._trx_err(
                        ev, "Session command 'new_session' missing 'participants' field"
                    )
                    return
                else:
                    participants = chat_cmd["participants"]
                    if isinstance(participants, list) is False:
                        participants = [participants]
                if "originator_username" not in chat_cmd:
                    self.log.error(
                        f"Session command 'new_session' missing 'originator_username' field: {ev.data}"
                    )
                    self._trx_err(
                        ev,
                        "Session command 'new_session' missing 'originator_username' field",
                    )
                    return
                else:
                    originator_username = chat_cmd["originator_username"]
                if originator_username not in participants:
                    participants.append(originator_username)
                is_new_session = True
                for session in self.chat_sessions:
                    if self.chat_sessions[session]["participants"] == participants:
                        session_id = session
                        is_new_session = False
                        self.log.info(
                            f"Joining existing session {session_id} for {participants}"
                        )
                        break
                if is_new_session is True:
                    session = {
                        "participants": participants,
                        "originator_username": originator_username,
                    }
                    session_id = str(uuid.uuid4())
                    self.chat_sessions[session_id] = session
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
                rev.data_type = "session/new"
                rev.data = json.dumps(session_id)
                self.event_send(rev)
        elif IndraEvent.mqcmp(ev.domain, "$event/chat/#"):
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
            cur_session = None
            for session_id in self.chat_sessions:
                if chat_msg["session_id"] == session_id:
                    cur_session = session_id
                    break
            if cur_session is None:
                self.log.error(
                    f"Chat message {ev.data} from {ev.from_id} has invalid session_id: {chat_msg['session_id']}"
                )
                return
            participants = self.chat_sessions[cur_session]["participants"]
            self.log.info(
                f"Chat message from {chat_msg['user']} in session {cur_session} to {participants}"
            )
            if chat_msg["user"] not in participants:
                self.log.error(
                    f"Chat message {ev.data} from {ev.from_id} has invalid user: {chat_msg['user']}"
                )
                return
            if "sentiment" in self.annotate:
                self.log.info(
                    f"Annotating chat message from {chat_msg['user']} in session {cur_session}"
                )
                rev = IndraEvent()
                rev.domain = "$trx/sentiment"
                rev.from_id = f"{self.name}/annotate/sentiment"
                rev.data_type = "sentiment_data"
                sentiment_data = {
                    "text": chat_msg["message"],
                    "user": chat_msg["user"],
                    "session_id": chat_msg["session_id"],
                }
                rev.data = json.dumps(sentiment_data)
                key = rev.uuid4 + "-sentiment"
                self.async_dist[key] = {
                    "event": copy.copy(ev),
                    "session": cur_session,
                    "participants": participants,
                }
                self.event_send(rev)
            if "translation" in self.annotate:
                self.log.info(
                    f"Annotating chat message from {chat_msg['user']} in session {cur_session}"
                )
                rev = IndraEvent()
                rev.domain = "$trx/translation"
                rev.from_id = f"{self.name}/annotate/translation"
                rev.data_type = "translation_data"
                translation_data = {
                    "text": chat_msg["message"],
                    "lang_code": "de",
                    "max_length": 128,
                    "user": chat_msg["user"],
                    "session_id": chat_msg["session_id"],
                }
                rev.data = json.dumps(translation_data)
                key = rev.uuid4 + "-translation"
                self.async_dist[key] = {
                    "event": copy.copy(ev),
                    "session": cur_session,
                    "participants": participants,
                }
                self.event_send(rev)
            if "conversational" in self.annotate:
                self.log.info(
                    f"Annotating chat message from {chat_msg['user']} in session {cur_session}"
                )
                rev = IndraEvent()
                rev.domain = "$trx/conversational"
                rev.from_id = f"{self.name}/annotate/conversational"
                rev.data_type = "chat_data"
                chat_data = {
                    "text": chat_msg["message"],
                    "max_length": 1024,
                    "user": chat_msg["user"],
                    "session_id": chat_msg["session_id"],
                }
                rev.data = json.dumps(chat_data)
                key = rev.uuid4 + "-conversational"
                self.async_dist[key] = {
                    "event": copy.copy(ev),
                    "session": cur_session,
                    "participants": participants,
                }
                self.event_send(rev)

            self.distribute(ev, cur_session, participants)
        elif IndraEvent.mqcmp(ev.domain, f"{self.name}/annotate/#"):
            if ev.domain == f"{self.name}/annotate/sentiment":
                key = ev.uuid4 + "-sentiment"
                if key in self.async_dist:
                    self.log.info(f"Got annotation-reply sentiment, uuid={ev.uuid4}")
                    if ev.data_type == "sentiment":
                        sentiment = json.loads(ev.data)
                        rev = self.async_dist[key]["event"]
                        msg_data = json.loads(rev.data)
                        msg_data["sentiment"] = sentiment
                        rev.data = json.dumps(msg_data)
                        cur_session = self.async_dist[key]["session"]
                        participants = self.async_dist[key]["participants"]
                        del self.async_dist[key]
                        self.distribute(rev, cur_session, participants)
                    else:
                        self.log.error(f"Unknown annotation data type: {ev.data_type}")
                else:
                    self.log.warning(
                        f"Got annotation-reply, uuid={ev.uuid4}, but not found in async_dist"
                    )
            elif ev.domain == f"{self.name}/annotate/translation":
                key = ev.uuid4 + "-translation"
                if key in self.async_dist:
                    self.log.info(f"Got annotation-reply translation, uuid={ev.uuid4}")
                    if ev.data_type == "translation":
                        translation = json.loads(ev.data)
                        rev = self.async_dist[key]["event"]
                        msg_data = json.loads(rev.data)
                        msg_data["translation"] = translation["translation"]
                        msg_data["lang_code"] = translation["lang_code"]
                        rev.data = json.dumps(msg_data)
                        cur_session = self.async_dist[key]["session"]
                        participants = self.async_dist[key]["participants"]
                        del self.async_dist[key]
                        self.distribute(rev, cur_session, participants)
                    else:
                        self.log.error(f"Unknown annotation data type: {ev.data_type}")
                else:
                    self.log.warning(
                        f"Got annotation-reply, uuid={ev.uuid4}, but not found in async_dist"
                    )
            elif ev.domain == f"{self.name}/annotate/conversational":
                key = ev.uuid4 + "-conversational"
                if key in self.async_dist:
                    self.log.info(
                        f"Got annotation-reply conversational, uuid={ev.uuid4}"
                    )
                    if ev.data_type == "chat_reply":
                        reply = json.loads(ev.data)
                        rev = self.async_dist[key]["event"]
                        msg_data = json.loads(rev.data)
                        msg_data["message"] = reply["text"]
                        rev.data = json.dumps(msg_data)
                        cur_session = self.async_dist[key]["session"]
                        participants = self.async_dist[key]["participants"]
                        del self.async_dist[key]

                        self.distribute(rev, cur_session, participants)
                    else:
                        self.log.error(f"Unknown annotation data type: {ev.data_type}")
                else:
                    self.log.warning(
                        f"Got annotation-reply, uuid={ev.uuid4}, but not found in async_dist"
                    )
            else:
                self.log.warning(
                    f"Unknown annotation domain {ev.domain}, uuid={ev.uuid4}, ignored"
                )
        else:
            self.log.info(f"Got something: {ev.domain}, sent by {ev.from_id}, ignored")

    def distribute(self, ev: IndraEvent, cur_session: str, participants: list):
        for participant in participants:
            for user_session in self.user_sessions:
                if user_session["user"] == participant:
                    rev = IndraEvent()
                    rev.from_id = self.name
                    rev.data_type = ev.data_type
                    rev.parent_uuid4 = cur_session
                    rev.data = ev.data
                    rev.to_scope = ev.domain
                    rev.time_jd_start = IndraTime.datetime2julian(
                        datetime.datetime.now(tz=datetime.timezone.utc)
                    )
                    rev.time_jd_end = IndraTime.datetime2julian(
                        datetime.datetime.now(tz=datetime.timezone.utc)
                    )
                    rev.uuid4 = str(uuid.uuid4())
                    rev.domain = user_session["from_id"]
                    self.log.info(
                        f"Sending chat message to {participant} at {rev.domain}: {rev.data}"
                    )
                    self.event_send(rev)
