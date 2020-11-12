from trapy import listen, accept, dial, recv, send, close


server_host = "10.0.0.2"
server_port = 6
client_host = "10.0.0.1"
client_port = 7

print("-------------------Client-------------------")
client = dial(server_host + f":{server_port}", client_host + f":{client_port}")
# if client:
#     while True:
#         val = "12345"
#         send(client, bytes(val, "utf8"))
#         print("send data :" + str(val))
#         r = recv(client, 40)
#         print("data recived: ", r)
#         break
#     close(client)

