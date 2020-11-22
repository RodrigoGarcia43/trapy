import json


PORTS_FILE = "./files/ports.json"


class ConnException(Exception):
    pass


def get_port():
    with open(PORTS_FILE) as fp:
        busy_ports = json.load(fp)

    for port in range(int(2 ** 16)):
        if port in busy_ports:
            continue

        with open(PORTS_FILE, "w") as fp:
            json.dump(busy_ports + [port], fp=fp, ensure_ascii=False, indent=2)
        return port

    raise ConnException("no port available")


def bind(port):
    with open(PORTS_FILE) as fp:
        busy_ports = json.load(fp)
    if port in busy_ports:
        raise ConnException(f"port {port} is busy")
    with open(PORTS_FILE, "w") as fp:
        json.dump(busy_ports + [port], fp=fp, ensure_ascii=False, indent=2)


def close_port(port):
    with open(PORTS_FILE) as fp:
        busy_ports = json.load(fp)

    if port not in busy_ports:
        raise ConnException(f"port {port} is not busy")

    with open(PORTS_FILE, "w") as fp:
        json.dump(
            [p for p in busy_ports if p != port], fp=fp, ensure_ascii=False, indent=2,
        )
