"""H2 입력 계획 생성기.

기본 동작은 요청 계획(JSON)만 만든다. 실제 포털 요청은 이 파일에 넣지 않아
실측 담당자가 준비·검토 중인 환경에 영향을 주지 않는다.
"""
import argparse
import json
from pathlib import Path


def build_plan(username, petition_ids):
    """Return the three-or-more private-detail requests used for H2 validation."""
    if len(petition_ids) < 3:
        raise ValueError("H2에는 서로 다른 타인 민원 ID가 최소 3개 필요합니다.")
    return {
        "case_id": "H2",
        "username": username,
        "petition_ids": petition_ids,
        "expected_statuses": [403] * len(petition_ids),
        "requests": [
            {"method": "GET", "path": f"/api/v1/petitions/{petition_id}", "expected_status": 403}
            for petition_id in petition_ids
        ],
    }


def run_h2(portal_login, *, attacker, attacker_password, victim, victim_password,
           attacker_source="203.0.113.11", normal_source="203.0.113.100"):
    """Make the H2 input with fresh synthetic users and petitions only."""
    registered = portal_login("haedam-normal", normal_source, "register", victim, pw=victim_password)
    if registered["statuses"] != [201]:
        raise RuntimeError("H2 victim registration failed")
    victim_posts = portal_login("haedam-normal", normal_source, "post", victim, "3", pw=victim_password)
    petition_ids = victim_posts.get("ids", [])
    if victim_posts["statuses"] != [201, 201, 201] or len(set(petition_ids)) != 3:
        raise RuntimeError("H2 victim petitions were not created")
    registered = portal_login("haedam-attacker", attacker_source, "register", attacker, pw=attacker_password)
    if registered["statuses"] != [201]:
        raise RuntimeError("H2 attacker registration failed")
    denied = portal_login("haedam-attacker", attacker_source, "view", attacker,
                          "--ids=" + ",".join(map(str, petition_ids)), pw=attacker_password)
    if denied.get("login") != 200 or denied["statuses"] != [403, 403, 403]:
        raise RuntimeError("H2 did not make three foreign-petition denials")
    own_post = portal_login("haedam-attacker", attacker_source, "post", attacker, "1", pw=attacker_password)
    own_ids = own_post.get("ids", [])
    if own_post["statuses"] != [201] or len(own_ids) != 1:
        raise RuntimeError("H2 attacker self-petition was not created")
    own = portal_login("haedam-attacker", attacker_source, "view", attacker,
                       f"--ids={own_ids[0]}", pw=attacker_password)
    if own.get("login") != 200 or own["statuses"] != [200]:
        raise RuntimeError("H2 self-petition check failed")
    return {"attacker": attacker, "victim": victim, "victim_petition_ids": petition_ids,
            "attacker_petition_id": own_ids[0], "statuses": denied["statuses"], "own_status": own["statuses"][0]}


def main():
    parser = argparse.ArgumentParser(description="H2 타인 민원 반복 조회 요청 계획 생성")
    parser.add_argument("--username", required=True, help="조회 시도 시민 계정")
    parser.add_argument("--petition-id", type=int, action="append", required=True, dest="petition_ids",
                        help="타 시민 소유 민원 ID (최소 3회)")
    parser.add_argument("--out", type=Path, help="계획 JSON 저장 경로")
    args = parser.parse_args()

    plan = build_plan(args.username, args.petition_ids)
    text = json.dumps(plan, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
