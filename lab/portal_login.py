"""Portal login traffic from a lab container (S1 input and effect checks). Runs inside haedam-attacker / haedam-normal.

python portal_login.py --source 203.0.113.100 register USER   # password from env PW
python portal_login.py --source 203.0.113.11 fail USER 9       # random wrong passwords, never printed
python portal_login.py --source 203.0.113.100 login USER       # password from env PW
python portal_login.py --source 203.0.113.11 post USER 8        # log in (env PW), then file N petitions (H1)
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
    ap.add_argument("mode", choices=["register", "fail", "login", "post", "detail"])
    ap.add_argument("username")
    ap.add_argument("count", nargs="?", type=int, default=1)
    ap.add_argument("petition_ids", nargs="*")
    a = ap.parse_args()
    s = Session(a.source)
    out = {"csrf": s.csrf(), "statuses": []}
    if a.mode == "detail":
        status, raw = s.call("POST", "/api/v1/auth/login", {"username": a.username, "password": os.environ["PW"]})
        out["login"] = status
        if status == 200:
            s.token = json.loads(raw)["data"]["csrf_token"]
        for petition_id in [a.count, *a.petition_ids]:
            out["statuses"].append(s.call("GET", f"/api/v1/petitions/{petition_id}")[0])
        print(json.dumps(out))
        return
    if a.mode == "post":
        status, raw = s.call("POST", "/api/v1/auth/login", {"username": a.username, "password": os.environ["PW"]})
        out["login"] = status
        if status == 200:
            s.token = json.loads(raw)["data"]["csrf_token"]
        out["petition_ids"] = []
        for i in range(a.count):
            body = {"title": f"실습 민원 {i + 1}번 확인 요청", "content": "H1 실습용 합성 민원입니다. 처리하지 않아도 됩니다.", "category": "기타"}
            created, created_raw = s.call("POST", "/api/v1/petitions", body)
            out["statuses"].append(created)
            if created == 201:
                out["petition_ids"].append(json.loads(created_raw)["data"]["id"])
        out["list"] = s.call("GET", "/api/v1/petitions")[0]
        print(json.dumps(out))
        return
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
