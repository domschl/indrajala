import json
import datetime
import uuid

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
        self.sessions = {}
        self.users = {}
        self.subscribe(["$trx/cs/#", "$event/chat/#", "$interactive/session/#"])

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
        if IndraEvent.mqcmp(ev.domain, "$interactive/session/#"):
            comps = ev.domain.split("/")
            if len(comps) < 4:
                self.log.error(f"Invalid session event: {ev.domain}")
                return
            if comps[2] == "start":
                user = comps[3]
                session_data = json.loads(ev.data)
                req_fields = ["session_id", "user", "from_id"]
                for field in req_fields:
                    if field not in session_data:
                        self.log.error(f"Session start missing required field: {field}")
                        return
                self.users[session_data["session_id"]] = session_data
                self.log.info(
                    f"User {user} started an interactive session from {session_data['from_id']}"
                )
            elif comps[2] == "end":
                user = comps[3]
                session_id = json.loads(ev.data)
                if session_id not in self.users:
                    self.log.warning(f"Session {session_id} by {user} does not exist")
                    return
                else:
                    if user != self.users[session_id]["user"]:
                        self.log.warning(
                            f"User {user} is not the owner of session {session_id}, actual owner is {self.users[session_id]['user']}"
                        )
                        return
                    self.log.info(
                        f"User {user} ended an interactive session {session_id} from {self.users[session_id]['from_id']}"
                    )
                del self.users[session_id]
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
            if chat_cmd["cmd"] == "register_user":
                if "user" not in chat_cmd:
                    self.log.error(
                        f"Session command 'register_user' missing 'user' field: {ev.data}"
                    )
                    self._trx_err(
                        ev, "Session command 'register_user' missing 'user' field"
                    )
                    return
            elif chat_cmd["cmd"] == "new_session":
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
                session_id = str(uuid.uuid4())
                session = {
                    "participants": participants,
                    "originator_username": originator_username,
                }
                self.sessions[session_id] = session
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
                rev.data_type = "session/new"
                rev.data = json.dumps(session_id)
                self.event_queue.put(rev)

        elif IndraEvent.mqcmp(ev.domain, "$event/chat/#"):
            pass
        else:
            self.log.info(f"Got something: {ev.domain}, sent by {ev.from_id}, ignored")
