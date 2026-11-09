"""Portal login traffic from a lab container (S1 input and effect checks). Runs inside haedam-attacker / haedam-normal.

python portal_login.py --source 203.0.113.100 register USER   # password from env PW
python portal_login.py --source 203.0.113.11 fail USER 9       # random wrong passwords, never printed
python portal_login.py --source 203.0.113.100 login USER       # password from env PW
Prints one JSON line: the HTTP status of every request. Bodies, cookies and passwords are never printed.
"""
import argparse
import http.client
import json
import os
import secrets
from http.cookies import SimpleCookie

HOST = "203.0.113.1"  # pfSense WAN → portal


class Session:
    def __init__(self, source):
        self.source, self.cookies, self.token = source, SimpleCookie(), None

    def call(self, method, path, body=None):
        conn = http.client.HTTPConnection(HOST, 80, timeout=10, source_address=(self.source, 0))
        headers = {"Connection": "close"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["X-CSRF-Token"] = self.token
        if "haedam_session" in self.cookies:
            headers["Cookie"] = "haedam_session=" + self.cookies["haedam_session"].value
        try:
            conn.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
            r = conn.getresponse()
            for k, v in r.getheaders():
                if k.lower() == "set-cookie":
                    self.cookies.load(v)
            raw = r.read()
            return r.status, raw
        except OSError:
            return 0, b""  # connection refused/timed out (e.g. pfSense block)
        finally:
            conn.close()

    def csrf(self):
        status, raw = self.call("GET", "/api/v1/auth/me")
        if status == 200:
            self.token = json.loads(raw)["data"].get("csrf_token")
        return status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("mode", choices=["register", "fail", "login"])
    ap.add_argument("username")
    ap.add_argument("count", nargs="?", type=int, default=1)
    a = ap.parse_args()
    s = Session(a.source)
    out = {"csrf": s.csrf(), "statuses": []}
    for _ in range(a.count):
        if a.mode == "register":
            body = {"username": a.username, "display_name": "실습계정", "password": os.environ["PW"]}
            path = "/api/v1/auth/register"
        else:
            pw = os.environ["PW"] if a.mode == "login" else "Synthetic-wrong-" + secrets.token_hex(8)
            body, path = {"username": a.username, "password": pw}, "/api/v1/auth/login"
        out["statuses"].append(s.call("POST", path, body)[0])
    print(json.dumps(out))


if __name__ == "__main__":
    main()
