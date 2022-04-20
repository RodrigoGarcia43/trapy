from trapy import dial, close, send, recv
import time

server_host = "10.0.0.2"
server_port = 6


print("-------------------Client-------------------")
client = dial(server_host + f":{server_port}")
# for _ in range(30):
timer = time.time()
val = "tres tristes tigres tragaban trigo en un trigal" * 5000
print(send(client, bytes(val, "utf8")))
# while True:
# r = recv(client, 1000000000000000000000000000000000000000000)
# print("data recived: ", r)
# print(time.time() - timer)
close(client)
