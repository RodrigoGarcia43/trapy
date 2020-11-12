import sys, socket, time, random
from struct import pack, unpack
import logging

from utils import parse_address


class Conn:
    def __init__(self, sock=None):
        if sock is None:
            self.socket = socket.socket(
                socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP
            )
        else:
            self.socket = sock

        self.server_host = None
        self.server_port = None
        self.client_host = None
        self.client_port = None


class ConnException(Exception):
    pass


def listen(address: str) -> Conn:
    conn = Conn()

    host, port = parse_address(address)

    print("socket binded to: " + address)
    conn.server_host, conn.server_port = host, port
    conn.socket.bind((host, port))

    return conn


def accept(conn) -> Conn:
    data, address = conn.socket.recvfrom(1024)
    ip_header, tcp_header, _ = get_packet(data)

    if not verify_checksum(ip_header, tcp_header):
        print("field checksum to accept conection from: " + str(address))

    if tcp_header[5] >> 1 != 1:
        print(
            "field to accept conection from: " + str(address) + " syn flag has value 0"
        )

    new_conn = Conn()
    new_conn.server_host, new_conn.server_port = conn.server_host, conn.server_port + 1
    new_conn.client_host = address[0]
    new_conn.client_port = address[1]
    new_conn.socket.bind((new_conn.server_host, new_conn.server_port))

    print("accepted connection from: " + str(address))

    return conn


def dial(server_address, client_address) -> Conn:
    conn = Conn()

    conn.server_host, conn.server_port = parse_address(server_address)
    conn.client_host, conn.client_port = parse_address(client_address)

    ip_header = build_ip_header(conn.server_host, conn.client_host)
    tcp_header = build_tcp_header(
        conn.server_host, conn.client_host, conn.server_port, conn.client_port, syn=1
    )
    packet = ip_header + tcp_header

    ip_header = unpack("!BBHHHBBH4s4s", packet[0:20])

    tcp_header = unpack("!HHLLBBHHH", packet[20:40])

    print("dial to: " + server_address)
    conn.socket.sendto(packet, (conn.server_host, conn.server_port))
    conn.socket.bind()

    return conn


def send(conn: Conn, data: bytes) -> int:
    ip_header = b"\x45\x00\x00\x28"  # Version, IHL, Type of Service | Total Length
    ip_header += b"\xab\xcd\x00\x00"  # Identification | Flags, Fragment Offset
    ip_header += b"\x40\x06\xa6\xec"  # TTL, Protocol | Header Checksum
    ip_header += b"\x0a\x00\x00\x01"  # Source Address
    ip_header += b"\x0a\x00\x00\x02"  # Destination Address

    tcp_header = b"\x30\x39\x00\x50"  # Source Port | Destination Port
    tcp_header += b"\x00\x00\x00\x00"  # Sequence Number
    tcp_header += b"\x00\x00\x00\x00"  # Acknowledgement Number
    tcp_header += b"\x50\x02\x71\x10"  # Data Offset, Reserved, Flags | Window Size
    tcp_header += b"\xe6\x32\x00\x00"  # Checksum | Urgent Pointer

    packet = ip_header + tcp_header
    conn.socket.sendto(packet, (conn.host, conn.port))


def recv(conn: Conn, length: int) -> bytes:
    conn.socket.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
    return conn.socket.recvfrom(65565)


def close(conn: Conn):
    conn.socket.close()
    conn.socket = None


def build_ip_header(source_ip, dest_ip, data_len=0):
    ip_ihl = 5
    ip_ver = 4
    ip_tos = 0
    ip_tot_len = 40 + data_len
    ip_id = random.randint(10000, 50000)
    ip_frag_off = 0
    ip_ttl = 255
    ip_proto = socket.IPPROTO_TCP
    ip_check = 0
    ip_saddr = socket.inet_aton(source_ip)
    ip_daddr = socket.inet_aton(dest_ip)

    ip_ihl_ver = (ip_ver << 4) + ip_ihl

    ip_header = pack(
        "!BBHHHBBH4s4s",
        ip_ihl_ver,
        ip_tos,
        ip_tot_len,
        ip_id,
        ip_frag_off,
        ip_ttl,
        ip_proto,
        ip_check,
        ip_saddr,
        ip_daddr,
    )
    ip_check = get_checksum(ip_header)
    ip_header = pack(
        "!BBHHHBBH4s4s",
        ip_ihl_ver,
        ip_tos,
        ip_tot_len,
        ip_id,
        ip_frag_off,
        ip_ttl,
        ip_proto,
        ip_check,
        ip_saddr,
        ip_daddr,
    )

    return ip_header


def build_tcp_header(source_ip, dest_ip, source_port, dest_port, data=None, syn=0):

    tcp_source = source_port
    tcp_dest = dest_port
    tcp_seq = 454
    tcp_ack_seq = 0
    tcp_doff = 5  # 4 bit field, size of tcp header, 5 * 4 = 20 bytes
    tcp_fin = 0
    tcp_syn = syn
    tcp_rst = 0
    tcp_psh = 0
    tcp_ack = 0
    tcp_urg = 0
    tcp_window = socket.htons(5840)  # 	maximum allowed window size
    tcp_check = 0
    tcp_urg_ptr = 0

    tcp_offset_res = (tcp_doff << 4) + 0
    tcp_flags = (
        tcp_fin
        + (tcp_syn << 1)
        + (tcp_rst << 2)
        + (tcp_psh << 3)
        + (tcp_ack << 4)
        + (tcp_urg << 5)
    )

    # the ! in the pack format string means network order
    tcp_header = pack(
        "!HHLLBBHHH",
        tcp_source,
        tcp_dest,
        tcp_seq,
        tcp_ack_seq,
        tcp_offset_res,
        tcp_flags,
        tcp_window,
        tcp_check,
        tcp_urg_ptr,
    )

    # pseudo header fields
    source_address = socket.inet_aton(source_ip)
    dest_address = socket.inet_aton(dest_ip)
    placeholder = 0
    protocol = socket.IPPROTO_TCP

    if data is not None:
        tcp_length = 20 + len(str(data))
    else:
        tcp_length = 20

    pseudo_header = pack(
        "!4s4sBBH", source_address, dest_address, placeholder, protocol, tcp_length
    )

    pseudo_header = pseudo_header + tcp_header
    if data is not None:
        pseudo_header = pseudo_header + bytes(data)

    tcp_check = get_checksum(pseudo_header)

    # make the tcp header again and fill the correct checksum - remember checksum is NOT in network byte order
    tcp_header = pack(
        "!HHLLBBHHH",
        tcp_source,
        tcp_dest,
        tcp_seq,
        tcp_ack_seq,
        tcp_offset_res,
        tcp_flags,
        tcp_window,
        tcp_check,
        tcp_urg_ptr,
    )
    return tcp_header


def get_checksum(data):
    sum = 0
    for index in range(0, len(data), 2):
        word = (data[index] << 8) + (data[index + 1])
        sum = sum + word
    sum = (sum >> 16) + (sum & 0xFFFF)
    sum = ~sum & 0xFFFF
    return sum


def get_packet(data):
    ip_header = data[20:40]
    ip_header = unpack("!BBHHHBBH4s4s", ip_header)

    tcp_header = data[40:60]
    tcp_header = unpack("!HHLLBBHHH", tcp_header)

    data = data[40:]
    return ip_header, tcp_header, data


def verify_checksum(ip_header, tcp_header, data=None):
    placeholder = 0
    if data is not None:
        tcp_length = 20 + len(data)
    else:
        tcp_length = 20
    protocol = ip_header[6]
    sourceIP = ip_header[8]
    destIP = ip_header[9]

    received_tcp_segment = pack(
        "!HHLLBBHHH",
        tcp_header[0],
        tcp_header[1],
        tcp_header[2],
        tcp_header[3],
        tcp_header[4],
        tcp_header[5],
        tcp_header[6],
        0,
        tcp_header[8],
    )
    pseudo_hdr = pack("!4s4sBBH", sourceIP, destIP, placeholder, protocol, tcp_length)
    total_msg = pseudo_hdr + received_tcp_segment
    if data is not None:
        total_msg += data

    checksum_from_packet = tcp_header[7]
    tcp_checksum = get_checksum(total_msg)
    print(checksum_from_packet)
    print(tcp_checksum)
    return checksum_from_packet == tcp_checksum

