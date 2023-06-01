import json
import datetime
import asyncio
import websockets
import websockets.client
import logging
import ssl
import uuid
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

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
        :param from_id:       originator-path, used for replies in transaction-mode
        :param uuid4:         unique id, is unchanged over transactions, can thus be used as correlator
        :param to_scope:      session scope as domain hierarchy, identifies sessions or groups, can imply security scope or context
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

class IndraClient:
    def __init__(self, config_file="indra_client.toml"):
        self.log = logging.getLogger("IndraClient")
        self.initialized = self.get_config(config_file, verbose=False)
        
    def get_config(self, config_file, verbose=True):
        valid = True
        try:
            self.config = tomllib.load(config_file)
        except Exception as e:
            self.config = {}
            self.config["uri"] = "ws://localhost:8083"
            if verbose is True:
                self.log.error("f{config_file} config file not found: {e}")
            return False
        if 'uri' not in self.config:
            self.config["uri"]="ws://localhost:8083"
            if verbose is True:
                self.log.error(f"Please provide an uri=ws[s]://host:port in {config_file}")
        
   
    async def init_connection(self):
        if "ssl" in self.config:
            use_ssl = self.config["ssl"] 
        else:
            use_ssl = False

        if use_ssl is True:
            ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            if "ca_authority" in self.config and self.config["ca_authority"] != "":
                ssl_ctx.load_verify_locations(cafile=self.config["ca_authority"])
        else:
            ssl_ctx = None
        async with websockets.client.connect(self.config["uri"], ssl=ssl_ctx) as websocket:
            print("CONNECTED")
            ie = IndraEvent(
                "$cmd/subs",
                "ws/python",
                str(uuid.uuid4()),
                "to/test",
                IndraEvent.datetime2julian(datetime.datetime.utcnow()),
                "string/test",
                json.dumps(["$event/omu/enviro-master/#"]),
                "hash",
                IndraEvent.datetime2julian(datetime.datetime.utcnow()),
            )
            # print(ie.to_json())
            # await asyncio.sleep(1)
            await websocket.send(ie.to_json())
            print("SENT")
            while True:
                try:
                    message = await websocket.recv()
                    print(message)
                except Exception as e:
                    print(e)
                    break
    #@staticmethod
    #parse_url(url):
		
async def indra(config):
    """Connect to Indra server, use TLS"""
    url = config["url"]
    ssl_ctx = None

            

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    config_file = "ws_indra.toml"
    wscl = IndraClient(config_file)
    asyncio.run(wscl.init_connection())
