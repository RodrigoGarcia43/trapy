import socket
from trapy import Conn
from utils import _get_packet, verify_checksum

conn = Conn()
conn.socket.settimeout(100)

data, addres = conn.socket.recvfrom(65555)

conn.source_address = ("10.0.0.2", 6)
ip_header, tcp_header, data = _get_packet(data, conn)
data = b"aaaaaaaa"

print(data)
print(verify_checksum(ip_header, tcp_header, data))
