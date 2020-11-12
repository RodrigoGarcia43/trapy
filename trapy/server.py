from trapy import listen, accept, dial, recv, send, close

host = "10.0.0.2"
port = 6

print("-------------------SERVER-------------------")
server = listen(host + f":{port}")
while True:
    _server = accept(server)
    # while _server != None:
    #     r = recv(_server, 40)
    #     print("data recived: " + str(r))
    #     send(_server, r)
    #     print("data sent: " + str(r))
close(server)
