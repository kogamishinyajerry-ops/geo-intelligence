from geo.monitoring.run import _counts, _exit_code, alert_markdown, notion_payload


def _diff(alerts, baseline=False, segment="A", _from="2026-06-07T00:00:00+00:00", to="2026-06-14T00:00:00+00:00"):
    return {"from": _from, "to": to, "segment": segment, "baseline": baseline, "alerts": list(alerts)}


def test_counts_buckets_by_level():
    d = _diff([{"level": "P1", "kind": "k", "msg": "m"}, {"level": "P3", "kind": "k", "msg": "m"},
               {"level": "P3", "kind": "k", "msg": "m"}])
    assert _counts(d) == {"total": 3, "P1": 1, "P2": 0, "P3": 2}


def test_exit_code_priority():
    assert _exit_code(_diff([])) == 0
    assert _exit_code(_diff([{"level": "P3", "kind": "k", "msg": "m"}])) == 1
    assert _exit_code(_diff([{"level": "P1", "kind": "k", "msg": "m"}])) == 2  # P1 优先于总数


def test_alert_markdown_contains_meta_and_body():
    d = _diff([{"level": "P1", "kind": "品牌空位被占", "msg": "竞品X 进来了"}])
    md = alert_markdown(d, n_captures=12)
    assert "细分 A" in md and "12 captures" in md
    assert "P1=1" in md
    assert "竞品X 进来了" in md


def test_notion_payload_shape_and_decoupled():
    d = _diff([{"level": "P2", "kind": "新对手", "msg": "对手站进入"}])
    p = notion_payload(d, n_captures=12, snapshot_file="A-20260614T000000Z.json")
    assert p["segment"] == "A"
    assert p["counts"] == {"total": 1, "P1": 0, "P2": 1, "P3": 0}
    assert p["snapshot_file"] == "A-20260614T000000Z.json"
    assert p["alerts"][0]["kind"] == "新对手"
    assert p["baseline"] is False


def test_notion_payload_baseline():
    d = _diff([], baseline=True, _from=None)
    p = notion_payload(d, n_captures=12, snapshot_file="A-x.json")
    assert p["baseline"] is True and p["counts"]["total"] == 0
