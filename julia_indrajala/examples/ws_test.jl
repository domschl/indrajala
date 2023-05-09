using HTTP.WebSockets
using MbedTLS
using UUIDs
using JSON3
using Dates
# using HTTP.IOExtras

struct IndraEvent
    domain::String
    from_id::String
    uuid4::UUID
    to_scope::String
    time_jd_start::Float64
    data_type::String
    data
    auth_has::String
    time_jd_end::Float64
end;

function new(domain::String, from_id::String, uuid4::UUID, to_scope::String, time_jd_start::Float64, data_type::String, data, auth_has::String, time_jd_end::Float64) :: IndraEvent
    return IndraEvent(domain, from_id, uuid4, to_scope, time_jd_start, data_type, data, auth_has, time_jd_end)
end;

println("Starting...")
sslconfig = MbedTLS.SSLConfig(false)
# sslconfig = MbedTLS.SSLConfig("/home/dsc/certs/nineveh.pem", "/home/dsc/certs/nineveh-key.pem")
println("Opening...")
WebSockets.open("ws://localhost:8082", sslconfig=sslconfig) do ws
    x=0.0;
    for i in 1:10000
        jd=datetime2julian(now(UTC))
        x = x + (rand()-0.5)/10.0;
        msg = IndraEvent("\$event/julia/test", "", UUIDs.uuid4(), "data/test", jd, "number/float", x, "", jd)  
        println("Sending...$(i)")
        send(ws, JSON3.write(msg))
        # println("Receiving...$(i)")
        # s = receive(ws)
        # println("Received:$(s)")
        sleep(.0100)
    end
end;