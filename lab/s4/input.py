#!/usr/bin/env python3
"""Create an S4 input plan without sending requests to the portal.

The generated events mirror the Graylog S4 boundary: five failed logins and
one success, all from one username/source-IP pair.  This is an offline review
artifact; it never opens a socket, invokes Docker, or changes a stack service.
"""

import argparse
import ipaddress
import json
import re


USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


def build_plan(username: str, src_ip: str) -> dict:
    """Return the six S4 correlation events for one test identity."""
    if not USERNAME_RE.fullmatch(username):
        raise ValueError("username must use 1-64 letters, digits, _, ., or -")
    ipaddress.ip_address(src_ip)

    failures = [
        {
            "source": "haedam-portal",
            "rule": "login-bruteforce",
            "status": 401,
            "username": username,
            "src_ip": src_ip,
        }
        for _ in range(5)
    ]
    success = {
        "source": "haedam-portal",
        "rule": "login-success",
        "status": 200,
        "username": username,
        "src_ip": src_ip,
    }
    return {
        "case_id": "S4",
        "live_request": False,
        "purpose": "offline correlation-input review",
        "events": [*failures, success],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an offline S4 input plan")
    parser.add_argument("--username", default="zz_s4_test")
    parser.add_argument("--src-ip", default="203.0.113.22")
    args = parser.parse_args()
    print(json.dumps(build_plan(args.username, args.src_ip), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
