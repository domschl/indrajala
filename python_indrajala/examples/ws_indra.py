import json
import datetime
import asyncio
import websockets
import logging
import ssl
import uuid
import toml


class IndraEvent:
    def __init__(
        self,
        domain,
        from_id,
        uuid4,
        to_scope,
        time_start,
        data_type,
        data,
        auth_hash=None,
        time_end=None,
    ):
        """Create an IndraEvent json object

        :param domain:        MQTT-like path
        :param from_id:       originator-path
        :param uuid4:         unique id
        :param to_scope:      security scope or context
        :param time_jd_start:    event time as float julian date
        :param data_type      short descriptor-path
        :param data           JSON data (note: simple values are valid)
        :param auth_hash:     security auth (optional)
        :param time_jd_end:      end-of-event jd (optional)
        """
        self.domain = domain
        self.from_id = from_id
        self.uuid4 = uuid4
        self.to_scope = to_scope
        self.time_jd_start = time_start
        self.data_type = data_type
        self.data = data
        self.auth_hash = auth_hash
        self.time_jd_end = time_end

    def to_json(self):
        """Convert to JSON string"""
        return json.dumps(self.__dict__)

    @staticmethod
    def datetime2julian(dt: datetime.datetime):
        """Convert datetime to Julian date"""
        return (
            dt.toordinal()
            + 1721425.5
            + (dt.hour / 24)
            + (dt.minute / 1440)
            + (dt.second / 86400)
            + (dt.microsecond / 86400000000)
        )

    @staticmethod
    def julian2datetime(jd):
        """Convert Julian date to datetime"""
        jd = jd + 0.5
        Z = int(jd)
        F = jd - Z
        if Z < 2299161:
            A = Z
        else:
            alpha = int((Z - 1867216.25) / 36524.25)
            A = Z + 1 + alpha - int(alpha / 4)
        B = A + 1524
        C = int((B - 122.1) / 365.25)
        D = int(365.25 * C)
        E = int((B - D) / 30.6001)
        day = B - D - int(30.6001 * E) + F
        if E < 14:
            month = E - 1
        else:
            month = E - 13
        if month > 2:
            year = C - 4716
        else:
            year = C - 4715
        hour = 24 * (jd - int(jd))
        minute = 60 * (hour - int(hour))
        second = 60 * (minute - int(minute))
        microsecond = 1000000 * (second - int(second))
        return datetime.datetime(
            year, month, int(day), int(hour), int(minute), int(second), int(microsecond)
        )


async def indra(config):
    """Connect to Indra server, use TLS"""
    url = config["url"]
    ssl_ctx = None
    if "ssl" in config and config["ssl"] is True:
        ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        if "ca_authority" in config and config["ca_authority"] != "":
            ssl_ctx.load_verify_locations(cafile=config["ca_authority"])
    async with websockets.connect(url, ssl=ssl_ctx) as websocket:
        ie = IndraEvent(
            "$event/python/test",
            "ws/python",
            str(uuid.uuid4()),
            "to/test",
            IndraEvent.datetime2julian(datetime.datetime.utcnow()),
            "string/test",
            "3.1325",
            "hash",
            IndraEvent.datetime2julian(datetime.datetime.utcnow()),
        )
        await websocket.send(ie.to_json())

        while True:
            try:
                message = await websocket.recv()
                print(message)
            except Exception as e:
                print(e)
                break


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    config = toml.load("ws_indra.toml")
    url = config["url"]
    asyncio.run(indra(config))
