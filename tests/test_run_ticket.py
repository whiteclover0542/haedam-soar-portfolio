from datetime import datetime, timedelta, timezone

from lab.run_ticket import SEAT, SRC, WINDOW_MIN, mttd, precheck, window_blocked

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)


def test_window_blocks_rerun_within_15min():
    assert window_blocked(NOW - timedelta(minutes=10), NOW, 15) == 300


def test_window_allows_after():
    assert window_blocked(NOW - timedelta(minutes=16), NOW, 15) is None
    assert window_blocked(None, NOW, 15) is None


def test_precheck_flags_leftover():
    assert precheck(["203.0.113.22"], [], "203.0.113.22") == ["portal_block_left:203.0.113.22"]


def test_precheck_flags_pf_leftover():
    assert precheck([], ["203.0.113.22"], "203.0.113.22") == ["pf_block_left:203.0.113.22"]


def test_precheck_clean():
    assert precheck(["203.0.113.99"], [], "203.0.113.22") == []


def test_mttd_seconds():
    assert mttd(NOW, NOW + timedelta(seconds=49, milliseconds=281)) == 49.281


def test_h2_is_available_to_the_same_command_runner_as_other_cases():
    assert SRC["H2"] == "203.0.113.11"
    assert SEAT["H2"] == "C"
    assert WINDOW_MIN["H2"] == 5
