using HTTP.WebSockets
using MbedTLS
using UUIDs
using JSON3
using Dates
using StructTypes
# using Copy
# using HTTP.IOExtras

Base.@kwdef mutable struct IndraEvent
    domain::String
    from_id::String
    uuid4::UUID
    parent_uuid4::String
    seq_no::Int64
    to_scope::String
    time_jd_start::Float64
    data_type::String
    data::String
    auth_hash::Any
    time_jd_end::Any
end;
StructTypes.StructType(::Type{IndraEvent}) = StructTypes.Mutable()

function indra_subscribe(ws, topics)
    msg = IndraEvent("\$cmd/subs", "ws/julia", UUIDs.uuid4(), "", 0, "cmd/subs", datetime2julian(now(UTC)), "cmd/subs", JSON3.write(topics), "", datetime2julian(now(UTC)))
    send(ws, JSON3.write(msg))
    return (msg)
end;

function indra_log(ws, type, msg)
    valid_types = ["error", "warn", "info", "debug"]
    if type in valid_types
        msg = IndraEvent("\$log/$type", "ws/julia", UUIDs.uuid4(), "", 0, "log/$type", datetime2julian(now(UTC)), "string", JSON3.read(JSON3.write(msg)), "", datetime2julian(now(UTC)))
    else
        msg = IndraEvent("\$log/error", "ws/julia", UUIDs.uuid4(), "", 0, "log/error", datetime2julian(now(UTC)), "string", JSON3.read(JSON3.write("Invalid log type: $type")), "", datetime2julian(now(UTC)))
    end
    send(ws, JSON3.write(msg))
    println("Sent: $(msg)")
    return (msg)
end;

sslconfig = MbedTLS.SSLConfig(false)
WebSockets.open("ws://localhost:8083") do ws # , sslconfig=sslconfig) do ws
    indra_log(ws, "info", "Connected to IndraJala from Julia")
    msg = indra_subscribe(ws, ["\$event/omu/#"])
    for rmsg in ws
        indra_log(ws, "warn", "Received: $(rmsg)")
    end
end;
