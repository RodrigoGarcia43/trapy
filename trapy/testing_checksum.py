from utils import build_tcp_header
import socket
from trapy import Conn

conn = Conn()

data_to_send = b"asdasd"
tcp_header = build_tcp_header(1, 6, 15, 17, data=data_to_send)
packet = tcp_header + data_to_send

conn.socket.sendto(packet, ("10.0.0.2", 6))
