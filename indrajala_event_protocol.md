# A provisional collection of IndraEvents

```Note:``` This _will_ change! The protocol is still highly experimental.

## The IndraEvent

| Field | Type | Description | Example |
| ----- | ---- | ----------- | ------- |
| `domain` | String | MQTT-like path, publisher topic | `$event/sensor/temperature` |
| `from_id` | String | MQTT-like path, originator-path, used for replies in transaction-mode | `Ws.1/192.168.1.1:8083` |
| `uuid4` | UUID4 | unique id, is unchanged over transactions, can thus be used as correlator | `45ba88f6-5997-4aa4-9864-8683fdcdaf42` |
| `to_scope` | String | MQTT-like path, session scope as domain hierarchy, identifies sessions or groups, can imply security scope or context | e.g. `/chat/session/45ba88f6-5997-4aa4-9864-8683fdcdaf42` |
| `time_jd_start` | Float64 | event time as float julian date (Why JD? because not limited to 1AD dates, is used for asto- and geological timespans!) | `2460088.5710301` (that is 2023-05-24 01:42:17 (UTC)) | 
| `data_type` | String | MQTT-like path, describes data format of `data` field, short descriptor-path | `number/float` |
| `data` | String (JSON) | JSON data (note: simple values are valid) | `3.1415` |
| `param auth_hash` | String | security auth (optional) | `""`, TBD |
| `time_jd_end` | Float64 | end-of-event julian date (optional) | If the event is not a moment in time, but a time-span, this is the end-time | `2460088.5710301` (or empty) |

## Protocol elements

_This is a provisional collection of protocol elements that are currently used to test integration between different Indrajala parts. These definitions will change and are neither consistent nor final._

### Types of protocols

There are (currently) three different protocol classes, identified by different domain prefixes:

| domain prefix | description | example domain |
| ------------- | ----------- | -------------- |
| `$event/` | The default PUB messages has a domain that is prefixed by `$event\`, the remained of the domain is equivalent to MQTT's topic. | `$event/sensor/temperature` |
| `$cmd/` | Messages starting with `$cmd/` are commands that somehow alter the server's state | `$cmd/subs` |
| `$trx/` | Messages that are requests within a request/reply transaction pair, e.g. for database requests. Request and reply share the same `uuid`. | `$trx/db/req/event/history` |

### Subscribe to events from event router

- IndraClient -> IndraServer

| Field | Type | Value | Description |
| ----- | ---- | ----------- | ------- |
| `domain` | String | `$cmd/subs` | Send an array of subscription-wildcards in order start receiving events. |
| `from_id` | String | _Application identifier, will be overwritten by transport_ | The receiving transport on server-side inserts the addres of the originator, e.g. `Ws.1/192.168.1.1:8083` |
| `uuid4` | UUID4 | _a valid UUID4_ | is unchanged over transactions, can thus be used as correlator, example: 45ba88f6-5997-4aa4-9864-8683fdcdaf42 |
| `to_scope` | String | "" | Doesn't matter |
| `time_jd_start` | Float64 | `2460088.5710301` | Julian date of request |
| `data_type` | String | `vector/string` | the JSON data is a string array |
| `data` | String (JSON) | `["$event/abc/#', "my/path/something/#"]` | JSON String array of subscription topics (MQTT wildcard syntax) |
| `param auth_hash` | String |  `""` | TBD |
| `time_jd_end` | Float64 | set to `time_jd_start` | currently unused |

Note: There is no reply to this message, the server will simply start sending the requested events.

### Request history

While subscribing to events is just a basic functionality of any event router similar to MQTT,
Indrajala maintains additionally the entire event history and makes database-requests available
to access that event history:

- IndraClient -> IndraServer

