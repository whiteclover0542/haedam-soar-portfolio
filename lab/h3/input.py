#!/usr/bin/env python3
"""Generate a reviewable H3 input plan without contacting the portal."""

import argparse
import json
import re


USERNAME = re.compile(r"^zz_[A-Za-z0-9_.-]{1,37}$")


def build_plan(staff_username, petition_ids):
    if not USERNAME.fullmatch(staff_username):
        raise ValueError("staff_username must be a dedicated zz_ account")
    if len(petition_ids) != 3 or any(type(item) is not int or item < 1 for item in petition_ids):
        raise ValueError("exactly three positive petition ids are required")
    return {"case_id": "H3", "live_request": False, "staff_username": staff_username,
            "petition_ids": petition_ids, "required_updates": 3,
            "purpose": "offline H3 preflight review"}


def main():
    parser = argparse.ArgumentParser(description="Generate an offline H3 preflight plan")
    parser.add_argument("--staff", default="zz_h3_staff")
    parser.add_argument("petition_ids", nargs="*", type=int, default=[101, 102, 103])
    args = parser.parse_args()
    print(json.dumps(build_plan(args.staff, args.petition_ids), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
