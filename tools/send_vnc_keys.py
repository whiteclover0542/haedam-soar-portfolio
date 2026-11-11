"""Send literal text and Enter keys to an unauthenticated local RFB/VNC endpoint."""

import socket
import struct
import sys
import time


def read_exact(sock: socket.socket, count: int) -> bytes:
    data = bytearray()
    while len(data) < count:
        chunk = sock.recv(count - len(data))
        if not chunk:
            raise ConnectionError("VNC connection closed")
        data.extend(chunk)
    return bytes(data)


def key(sock: socket.socket, value: int) -> None:
    for down in (1, 0):
        sock.sendall(struct.pack(">BBHI", 4, down, 0, value))


def main(host: str, port: int, text: str) -> None:
    with socket.create_connection((host, port), timeout=15) as sock:
        read_exact(sock, 12)
        sock.sendall(b"RFB 003.008\n")
        types = read_exact(sock, read_exact(sock, 1)[0])
        if 1 not in types:
            raise RuntimeError(f"VNC security type 1 unavailable: {types!r}")
        sock.sendall(b"\x01")
        if struct.unpack(">I", read_exact(sock, 4))[0]:
            raise RuntimeError("VNC security negotiation failed")
        sock.sendall(b"\x01")
        read_exact(sock, 20)
        name_length = struct.unpack(">I", read_exact(sock, 4))[0]
        read_exact(sock, name_length)
        for character in text:
            key(sock, 0xFF0D if character == "\n" else ord(character))
        time.sleep(0.3)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3].replace("\\n", "\n"))
