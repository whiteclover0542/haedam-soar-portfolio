"""대기 케이스의 실행 전 계획만 출력한다. 네트워크·Docker·파일을 변경하지 않는다."""
import argparse
import json


PLANS = {
    "H3": {
        "title": "민원 처리 결과 조작",
        "required_inputs": ["staff_username", "petition_ids"],
        "preconditions": ["변경 이력·복원 API 배포", "전용 staff 계정", "원본 상태 스냅샷"],
        "expected": ["짧은 시간 대량 petition.updated 탐지", "권한 회수", "이력 기반 상태·답변 복원"],
    },
    "S4": {
        "title": "실패 뒤 성공 계정 잠금",
        "required_inputs": ["username", "source_ip"],
        "preconditions": ["S4 Graylog 정의 반입", "haedam-31·haedam-13 활성화", "전용 합성 시민 계정"],
        "expected": ["401 다섯 건 뒤 200 한 건", "계정 잠금·세션 회수", "새 로그인은 잠금 상태로 거부"],
    },
    "S7": {
        "title": "홈페이지 변조",
        "required_inputs": ["asset_id", "file_key"],
        "preconditions": ["Wazuh FIM·Graylog 경로 연결", "기준 해시 등록", "승인된 시험 파일 하나"],
        "expected": ["FIM과 웹 접근 신호 탐지", "변경 파일 복원 또는 새 파일 격리", "원본 해시 일치"],
    },
    "S12": {
        "title": "요청 폭주",
        "required_inputs": ["source_ip", "duration_seconds"],
        "preconditions": ["전용 기준선·health 측정", "다른 실측·배포와 시간 분리", "S12 Graylog·haedam-20 활성화 확인"],
        "expected": ["web.request 폭주 탐지", "공격 출발지 차단", "정상 사용자 health 회복"],
    },
}


def build_plan(case_id):
    """Return a data-only plan for a case that has not been connected to the panel."""
    item = PLANS[case_id]
    return {"case_id": case_id, "execution": False, **item}


def main():
    parser = argparse.ArgumentParser(description="대기 케이스 실행 전 계획 출력 (실행 없음)")
    parser.add_argument("case_id", choices=sorted(PLANS))
    args = parser.parse_args()
    print(json.dumps(build_plan(args.case_id), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
