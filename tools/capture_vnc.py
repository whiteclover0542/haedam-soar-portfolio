"""Capture a raw RFB/VNC framebuffer to a BMP without Docker-side tooling."""

import socket
import struct
import sys
from pathlib import Path


def read_exact(sock: socket.socket, count: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < count:
        data = sock.recv(count - len(chunks))
        if not data:
            raise ConnectionError("VNC connection closed")
        chunks.extend(data)
    return bytes(chunks)


def main(host: str, port: int, destination: Path) -> None:
    with socket.create_connection((host, port), timeout=15) as sock:
        read_exact(sock, 12)
        sock.sendall(b"RFB 003.008\n")
        security_count = read_exact(sock, 1)[0]
        security_types = read_exact(sock, security_count)
        if 1 not in security_types:
            raise RuntimeError(f"VNC security type 1 unavailable: {security_types!r}")
        sock.sendall(b"\x01")
        if struct.unpack(">I", read_exact(sock, 4))[0]:
            raise RuntimeError("VNC security negotiation failed")
        sock.sendall(b"\x01")
        width, height = struct.unpack(">HH", read_exact(sock, 4))
        read_exact(sock, 16)
        name_length = struct.unpack(">I", read_exact(sock, 4))[0]
        read_exact(sock, name_length)

        # 32-bit little-endian BGRX pixels make BMP serialization direct.
        sock.sendall(b"\x00\x00\x00\x00" + struct.pack(">BBBBHHHBBBxxx", 32, 24, 0, 1, 255, 255, 255, 16, 8, 0))
        sock.sendall(struct.pack(">BBHHHH", 3, 0, 0, 0, width, height))
        if read_exact(sock, 1) != b"\x00":
            raise RuntimeError("Unexpected VNC server message")
        read_exact(sock, 1)
        rectangles = struct.unpack(">H", read_exact(sock, 2))[0]
        canvas = bytearray(width * height * 3)
        for _ in range(rectangles):
            x, y, rect_width, rect_height, encoding = struct.unpack(">HHHHi", read_exact(sock, 12))
            if encoding != 0:
                raise RuntimeError(f"Unsupported VNC encoding: {encoding}")
            pixels = read_exact(sock, rect_width * rect_height * 4)
            for row in range(rect_height):
                source = row * rect_width * 4
                target = ((height - 1 - (y + row)) * width + x) * 3
                for column in range(rect_width):
                    pixel = source + column * 4
                    canvas[target + column * 3 : target + column * 3 + 3] = pixels[pixel : pixel + 3]

    size = 14 + 40 + len(canvas)
    header = b"BM" + struct.pack("<IHHI", size, 0, 0, 54)
    dib = struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24, 0, len(canvas), 2835, 2835, 0, 0)
    destination.write_bytes(header + dib + canvas)
    print(f"{width}x{height} -> {destination}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), Path(sys.argv[3]))
