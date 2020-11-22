from Mapper import Mapper
import random, socket, sys, time
from threading import Thread
from ports import get_port, bind, close_port

from threads import RecvTask

from utils import (
    parse_address,
    build_tcp_header,
    get_packet,
    _get_packet,
    clean_in_buffer,
)


class Conn:
    def __init__(self, sock=None, size=1024):
        if sock is None:
            self.socket = socket.socket(
                socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP
            )
        else:
            self.socket = sock

        self.fragment_size = size
        self.seq_limit = 2 ** 32
        self.seq = random.randint(0, self.seq_limit)
        # self.seq = 2 ** 32 - 1000

        self.ack = None

        self.source_address = None
        self.dest_address = None
        self.time_limit = 0.25
        self.time_errors_count = 1
        self.recived_buffer = b""

    def get_time_limit(self):
        result = self.time_limit
        self.time_limit = self.time_limit * 2
        self.time_errors_count += 1
        if self.time_errors_count == 10:
            return None
        return result

    def reset_time_limit(self):
        self.time_limit = 0.25
        self.time_errors_count = 1


class ConnException(Exception):
    pass


def listen(address: str) -> Conn:
    conn = Conn()

    print("socket binded to: " + address)
    conn.source_address = parse_address(address)
    bind(conn.source_address[1])

    return conn


def accept(conn, size=1024) -> Conn:
    while True:
        try:
            data, address = conn.socket.recvfrom(1024)
            ip_header, tcp_header, _ = _get_packet(data, conn)
        except (TypeError):
            continue

        if (tcp_header[5] >> 1 & 0x01) != 1:
            print(
                "field to accept conection from: "
                + str((address[0], tcp_header[0]))
                + " syn flag has value 0"
            )
            continue

        new_conn = Conn(size=size)
        new_conn.source_address = (
            conn.source_address[0],
            get_port(),
        )
        new_conn.dest_address = (address[0], tcp_header[0])

        print("accepted connection from: " + str((address[0], tcp_header[0])))

        resp_tcp_header = build_tcp_header(
            new_conn.source_address[1],
            new_conn.dest_address[1],
            new_conn.seq,
            tcp_header[2] + 1,
            syn=1,
        )

        packet = resp_tcp_header
        new_conn.socket.sendto(packet, new_conn.dest_address)

        new_conn.ack = tcp_header[2]

        reset = False
        time_limit = new_conn.get_time_limit()
        timer = time.time()
        conn.socket.settimeout(1)
        while True:
            if time_limit is None:
                reset = True
                break

            if time.time() - timer > time_limit:
                print("re-sending second SYN-ACK")
                timer = time.time()
                new_conn.socket.sendto(packet, new_conn.dest_address)
                time_limit = conn.get_time_limit()

            try:
                data, address = new_conn.socket.recvfrom(1024)

            except socket.timeout:
                continue

            try:
                _, _, _ = get_packet(data, new_conn)
                conn.reset_time_limit()
                break
            except TypeError:
                continue

        if reset:
            print("Reset accept")
            close(new_conn)
            continue

        print("Succesfull handshake")
        print((new_conn.seq, new_conn.ack))

        return new_conn


def dial(address, size=1024) -> Conn:
    conn = Conn(size=size)

    conn.dest_address = parse_address(address)
    source_port = get_port()
    tcp_header = build_tcp_header(source_port, conn.dest_address[1], conn.seq, 7, syn=1)
    packet = tcp_header

    print("dial to: " + str(address))

    conn.source_address = (conn.socket.getsockname()[0], source_port)
    conn.socket.sendto(packet, conn.dest_address)

    close_dial = False
    time_limit = conn.get_time_limit()
    timer = time.time()
    conn.socket.settimeout(1)
    while True:
        if time_limit is None:
            close_dial = True
            break

        if time.time() - timer > time_limit:
            print("re-sending SYN")
            conn.socket.sendto(packet, conn.dest_address)
            time_limit = conn.get_time_limit()
            timer = time.time()
            continue

        try:
            try:
                data, address = conn.socket.recvfrom(1024)
            except socket.timeout:
                continue

            ip_header, tcp_header, _ = _get_packet(data, conn)
            conn.reset_time_limit()
            break
        except TypeError:
            continue

    socket.setdefaulttimeout(None)
    if close_dial:
        raise ConnException("Dial Failed")

    conn.ack = tcp_header[2]

    conn.dest_address = (socket.inet_ntoa(ip_header[8]), tcp_header[0])

    print("Succesful handshake")
    print((conn.seq, conn.ack))

    new_tcp_header = build_tcp_header(0, conn.dest_address[1], conn.seq, conn.ack + 1)
    conn.socket.sendto(new_tcp_header, conn.dest_address)

    return conn


def send(conn: Conn, data: bytes) -> int:
    size = conn.fragment_size
    # TODO
    # window_size = min(max(1, int(len(data) / 10)), int(conn.seq_limit / 10)))
    window_size = 1024 * 20

    window = conn.seq
    duplicated_ack = 0
    mapper = Mapper(conn.seq, conn.seq_limit, len(data), window_size, size)
    recv_task = RecvTask()
    t = Thread(target=recv_task._recv, args=[conn])
    t.start()

    timer = None
    time_limit = conn.get_time_limit()

    while True:
        if time_limit is None:
            recv_task.stop()
            t.join()
            raise ConnException("Timeout")

        if len(recv_task.recived) > 0:
            conn.reset_time_limit()

            _, tcp_header, _ = recv_task.recived.pop(0)

            if (tcp_header[5] >> 4 & 0x01) != 1:
                continue

            ack = tcp_header[3] % conn.seq_limit
            print(ack)

            if mapper.get(ack) > mapper.get(window):
                if conn.seq != window:
                    timer = time.time()
                else:
                    timer = None

                window = ack % conn.seq_limit
                duplicated_ack = 0

                # print("ack -> " + str(ack))
                if mapper.get(ack) >= len(data):
                    recv_task.stop()
                    t.join()
                    return len(data)
            else:
                duplicated_ack += 1
                if duplicated_ack == 3:
                    recv_task.recived.clear()
                    conn.seq = ack % conn.seq_limit
                    duplicated_ack = 0

        if timer is not None and time.time() - timer > conn.time_limit:
            # print((conn.seq, window))
            conn.seq = window % conn.seq_limit
            time_limit = conn.get_time_limit()
            timer = time.time()

        if (mapper.get(conn.seq) < (mapper.get(window) + window_size)) and (
            mapper.get(conn.seq) < len(data)
        ):

            # if (
            #     (conn.seq - window <= window_size and conn.seq - window >= 0)
            #     or (
            #         ((conn.seq_limit - 1) - window + conn.seq) <= window_size
            #         and conn.seq - window < 0
            #     )
            # ) and (mapper.get(conn.seq) < len(data)):

            if timer is None:
                timer = time.time()

            if mapper.get(conn.seq) + size >= len(data):
                to_send = data[mapper.get(conn.seq) :]
                tcp_header = build_tcp_header(
                    conn.source_address[1],
                    conn.dest_address[1],
                    conn.seq,
                    3,
                    fin=1,
                    data=to_send,
                )
                packet = tcp_header + to_send
            else:
                to_send = data[mapper.get(conn.seq) : mapper.get(conn.seq) + size]
                tcp_header = build_tcp_header(
                    conn.source_address[1],
                    conn.dest_address[1],
                    conn.seq,
                    4,
                    data=to_send,
                )

                packet = tcp_header + to_send
            print("sending seq -> " + str(conn.seq))
            conn.socket.sendto(packet, conn.dest_address)
            conn.seq = (conn.seq + len(to_send)) % conn.seq_limit


def recv(conn: Conn, length: int) -> bytes:
    # recived_buffer = b""
    recv_task = RecvTask()
    t = Thread(target=recv_task._recv, args=[conn])
    t.start()
    timer = None
    time_limit = conn.get_time_limit()
    retr = 0
    while True:
        if time_limit is None:
            recv_task.is_runing = False
            t.join()
            clean_in_buffer(conn)
            raise ConnException("Timeout")

        if len(recv_task.recived) > 0:
            timer = time.time()
            conn.reset_time_limit()
            _, tcp_header, data = recv_task.recived.pop(0)

            if (tcp_header[5] >> 4 & 0x01) == 1:
                continue

            seq_recived = tcp_header[2]

            if len(data) == 0:
                continue

            if seq_recived == conn.ack:
                retr = 0
                conn.ack = (seq_recived + len(data)) % conn.seq_limit
                # print((seq_recived, conn.ack))

                conn.recived_buffer += data
                new_tcp_header = build_tcp_header(
                    conn.source_address[1], conn.dest_address[1], 7, conn.ack, _ack=1
                )
                # print(conn.ack)
                packet = new_tcp_header
                conn.socket.sendto(packet, conn.dest_address)
                if (tcp_header[5] & 0x01) == 1:
                    for _ in range(10):
                        conn.socket.sendto(packet, conn.dest_address)
                    recv_task.is_runing = False
                    t.join()
                    clean_in_buffer(conn)
                    print("AAAAAAAA")
                    if len(conn.recived_buffer) < length:
                        result = conn.recived_buffer[:]
                        conn.recived_buffer = b""
                        return result
                    else:
                        result = conn.recived_buffer[0:length]
                        conn.recived_buffer = conn.recived_buffer[length:]
                        return result

            else:
                # print((seq_recived, conn.ack))
                retr += 1
                if retr == 3:
                    retr = 0
                    recv_task.recived.clear()
                new_tcp_header = build_tcp_header(
                    conn.source_address[1], conn.dest_address[1], 7, conn.ack, _ack=1
                )
                # print(conn.ack)
                packet = new_tcp_header
                conn.socket.sendto(packet, conn.dest_address)

        if timer is not None and time.time() - timer > time_limit:
            timer = time.time()
            time_limit = conn.get_time_limit()
            print("re-sending ack " + str(conn.ack))
            new_tcp_header = build_tcp_header(
                conn.source_address[1], conn.dest_address[1], 7, conn.ack, _ack=1
            )
            print(conn.ack)
            packet = new_tcp_header
            conn.socket.sendto(packet, conn.dest_address)


def close(conn: Conn):
    conn.socket.close()
    conn.socket = None
    close_port(conn.source_address[1])
