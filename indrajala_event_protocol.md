# A provisional collection of IndraEvents

```Note:``` This _will_ change! The protocol is still highly experimental.

## The IndraEvent

| Field | Type | Description | Example |
| ----- | ---- | ----------- | ------- |
| `domain` | String | MQTT-like path, publisher topic | $event/sensor/temperature |
| `from_id` | String | MQTT-like path, originator-path, used for replies in transaction-mode | Ws.1/192.168.1.1:8083 |
| `uuid4` | UUID4 | unique id, is unchanged over transactions, can thus be used as correlator | 45ba88f6-5997-4aa4-9864-8683fdcdaf42 |
| `to_scope` | String | MQTT-like path, session scope as domain hierarchy, identifies sessions or groups, can imply security scope or context | /chat/session/45ba88f6-5997-4aa4-9864-8683fdcdaf42 |
| `time_jd_start` | Float64 | event time as float julian date (Why JD? because not limited to 1AD dates, is used for asto- and geological timespans!) | 2460088.5710301 (that is 2023-05-24 01:42:17 (UTC)) | 
| data_type | String | MQTT-like path, describes data format of `data` field, short descriptor-path | number/float |
| data | String (JSON) | JSON data (note: simple values are valid) | 3.1415 |
| param auth_hash | String | security auth (optional) | "", TBD |
| time_jd_end | Float64 | end-of-event julian date (optional) | If the event is not a moment in time, but a time-span, this is the end-time | 2460088.5710301 (or empty) |

## Protocol elements


