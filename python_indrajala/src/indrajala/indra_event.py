import json

class IndraTime:
    def __init__(self, timespec: str):
        self.timepec=timespec
        pass


class IndraEvent:
    def __init__(self, domain, from_instance, from_uuid4, to_scope, time_start, data_type, data, auth_hash=None, time_end=None):
        """ Create an IndraEvent json object

        :param domain:        MQTT-like path
        :param from_instance: originator-path
        :param from_uuid4:    unique id for originator
        :param to_scope:      security context
        :param auth_hash:     security auth (optional)
        :param time_start:    event time in ISO UTC XXXX paleo scale!
        :param time_end:      end-of-event (optional)
        :param data_type      short descriptor-path
        :param data           JSON data (note: simple values are valid)
        """
        self.domain = domain
        self.from_instance = from_instance
        self.from_uuid4 = from_uuid4
        self.to_scope = to_scope
        self.auth_hash = auth_hash
        self.time_start = time_start
        self.time_end = time_end
        self.data_type = data_type
        self.data = data

    def __call__(self):
        return json.dumps(self, default=vars)

