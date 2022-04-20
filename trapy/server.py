from trapy import listen, accept, close, recv, send

host = "10.0.0.2"
port = 6

print("-------------------SERVER-------------------")
server = listen(host + f":{port}")
_server = accept(server)
while True:
    r = recv(_server, 47)
    print("data recived: " + str(r))
# r = r.upper()
# print(send(_server, r))

close(server)
close(_server)
