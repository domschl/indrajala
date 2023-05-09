using HTTP.WebSockets
using MbedTLS
# using HTTP.IOExtras

println("Starting...")
sslconfig = MbedTLS.SSLConfig(false)
# sslconfig = MbedTLS.SSLConfig("/home/dsc/certs/nineveh.pem", "/home/dsc/certs/nineveh-key.pem")
println("Opening...")
WebSockets.open("ws://localhost:8082", sslconfig=sslconfig) do ws
    for i in 1:30
        println("Sending...$(i)")
        send(ws, "Hello")
        println("Receiving...$(i)")
        s = receive(ws)
        println("Received:$(s)")
    end
end;