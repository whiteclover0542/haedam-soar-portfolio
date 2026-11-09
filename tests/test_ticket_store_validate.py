import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/ticket-store"))
from ticket_store import dashboard, validate  # noqa: E402


def test_h1_detected_record_is_accepted():
    # haedam-35가 보내는 본문 그대로: 민원 도배는 계정 단위라 src_ip가 없다
    validate.record_body({"seat": "A", "case_id": "H1", "group_key": "zz_a_h1", "stage": "detected",
                          "title": "H1 민원 도배(작성 제한)", "asset_id": "haedam-portal", "src_ip": None,
                          "username": "zz_a_h1", "event_ids": ["01M6ZHATV8EA6T96HRE2JSKRP5"], "action": None})
    assert "H1" in dashboard.CASES
