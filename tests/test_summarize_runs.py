from tools.summarize_runs import summarize

OK_EFFECT = {"attacker": "403", "normal": "200"}


def row(case="S8", applied=True, mttd=1.0, normal="200", restored="200", **extra):
    r = {"case": case, "run_id": "x", "input_at": "2026-11-09T03:00:00+00:00", "mttd_s": mttd, "detect_to_block_s": 0.5,
         "actions": [["portal", "block", "applied" if applied else "failed", "2026-11-09T03:00:40+00:00"]],
         "effect": {"attacker": "403", "normal": normal}, "restore": {"attacker_after": restored}}
    r.update(extra)
    return r


def test_rates():
    s = summarize([row(), row(), row(applied=False)])
    assert s["S8"]["runs"] == 3 and s["S8"]["auto_rate"] == 2 / 3 and s["total"]["runs"] == 3


def test_median_ignores_failed():
    s = summarize([row(mttd=1.0), row(mttd=3.0), row(mttd=None, applied=False)])
    assert s["S8"]["runs"] == 3 and s["S8"]["mttd_median"] == 2.0


def test_s10_needs_pfsense_block():
    portal_only = row(case="S10", effect={"attacker": "000", "normal": "200"})
    both = row(case="S10", effect={"attacker": "000", "normal": "200"})
    both["actions"].append(["pfsense", "block", "applied", "2026-11-09T03:00:41+00:00"])
    assert summarize([portal_only, both])["S10"]["auto_rate"] == 1 / 2


def test_input_to_block_falls_back_to_actions():
    s = summarize([row()])
    assert s["S8"]["input_to_block_median"] == 40.0


def test_normal_impact_and_restore():
    s = summarize([row(normal="403"), row(restored="000"), row()])
    assert s["S8"]["normal_fail_runs"] == 1 and s["S8"]["restore_rate"] == 2 / 3


def test_h1_auto_ok_expects_429():
    r = row(case="H1", actions=[["portal", "restrict_posting", "applied", "2026-11-09T03:00:40+00:00"]],
            effect={"attacker": "429", "normal": "201"})
    assert summarize([r])["H1"]["auto_rate"] == 1.0


def test_baseline_rows_count_false_positives_only():
    s = summarize([row(case="H1", baseline=True, ticket_id="T-1"), row(case="H1", baseline=True, ticket_id=None), row(case="H1")])
    assert s["H1"]["runs"] == 1 and s["H1"]["false_positives"] == 1 and s["H1"]["baseline_runs"] == 2
