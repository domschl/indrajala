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
    to_scope::String
    time_jd_start::Float64
    data_type::String
    data::Any
    auth_has::Any
    time_jd_end::Any
end;
StructTypes.StructType(::Type{IndraEvent}) = StructTypes.Mutable()
# function new(domain::String, from_id::String, uuid4::UUID, to_scope::String, time_jd_start::Float64, data_type::String, data, auth_has::String, time_jd_end::Float64) :: IndraEvent
#     return IndraEvent(domain, from_id, uuid4, to_scope, time_jd_start, data_type, data, auth_has, time_jd_end)
# end;

function indra_subscribe(ws, topics)
    msg = IndraEvent("\$cmd/subs", "ws/julia", UUIDs.uuid4(), "cmd/subs", datetime2julian(now(UTC)), "cmd/subs", JSON3.read(JSON3.write(topics)), "", datetime2julian(now(UTC)))
    send(ws, JSON3.write(msg))
    return(msg)
end;

function indra_log(ws, type, msg)
    valid_types = ["error", "warn", "info", "debug"]
    if type in valid_types
        msg = IndraEvent("\$log/$type", "ws/julia", UUIDs.uuid4(), "log/$type", datetime2julian(now(UTC)), "string", JSON3.read(JSON3.write(msg)), "", datetime2julian(now(UTC)))
    else
        msg = IndraEvent("\$log/error", "ws/julia", UUIDs.uuid4(), "log/error", datetime2julian(now(UTC)), "string", JSON3.read(JSON3.write("Invalid log type: $type")), "", datetime2julian(now(UTC)))
    end
    send(ws, JSON3.write(msg))
    return(msg)
end;

sslconfig = MbedTLS.SSLConfig(false)
WebSockets.open("ws://localhost:8083", sslconfig=sslconfig) do ws
    msg = indra_subscribe(ws, ["omu/#"])
    for rmsg in ws
        indra_log(ws, "warn", "Received: $(rmsg)")
        wmsg = IndraEvent("", "", UUIDs.uuid4(), "", datetime2julian(now(UTC)), "cmd/subs", JSON3.read(JSON3.write(["omu/#"])), "", datetime2julian(now(UTC)))
        JSON3.read!(String(rmsg), wmsg)
        indra_log(ws, "error", "Received: $(msg)")
        # wmsg.domain = "\$log/" * msg.domain
        # send(ws, JSON3.write(wmsg))
    end
end;



#    x=0.0;
#    for i in 1:10
#        jd=datetime2julian(now(UTC))
#        x = x + (rand()-0.5)§10.0;
#        msg = IndraEvent("\$event/julia/test", "", UUIDs.uuid4(), "data/test", jd, "number/float", x, "", jd)  
#        println("Sending...$(i)")
#        send(ws, JSON3.write(msg))
#        # println("Receiving...$(i)")
#        # s = receive(ws)
#        # println("Received:$(s)")
#        sleep(1.00)
#    end
#end;
