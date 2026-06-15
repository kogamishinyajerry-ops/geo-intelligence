from datetime import datetime, timezone

from geo.evidence.schema import BuyerSegment, Capture, CitedSource
from geo.monitoring.diff import diff_snapshots, format_alerts
from geo.monitoring.snapshot import build_snapshot

_TS = datetime(2026, 6, 14, tzinfo=timezone.utc)


def _cap(brands, sources, query="q", seg=BuyerSegment.A):
    """sources: list of (domain, site_name, auth, freshness)。"""
    cs = [
        CitedSource(url=f"https://{d}/p", domain=d, site_name=sn, auth_score=a, freshness_score=fr)
        for (d, sn, a, fr) in sources
    ]
    raw = " ".join(brands) or "generic"
    return Capture(
        id=Capture.make_id("t", seg.value, _TS, raw + query + repr(sources)),
        engine="t", query=query, buyer_segment=seg, timestamp=_TS,
        raw_answer=raw, named_brands=list(brands), cited_sources=cs,
    )


def test_build_snapshot_shape_and_traceability():
    caps = [
        _cap(["华为"], [("a.com", "SiteA", 0.5, 0.9)], query="q1"),
        _cap([], [("b.com", "SiteB", 0.3, 0.8)], query="q2"),
    ]
    snap = build_snapshot(caps, "A", now=_TS)
    assert snap["snapshot_version"] == "1.0"
    assert snap["segment"] == "A"
    assert snap["n_captures"] == 2
    # 可回溯：capture_ids == 输入且有序（红线 #1/#2）
    assert snap["capture_ids"] == sorted(c.id for c in caps)
    assert snap["captured_at"] == _TS.isoformat()
    # 指标已接好
    assert {r["domain"] for r in snap["citation_leaderboard"]} == {"a.com", "b.com"}
    assert snap["brand_sov"] == {"华为": 1.0}
    assert len(snap["per_query"]) == 2


# ── diff：用手搭快照 dict 隔离测对比逻辑 ──

def _snap(segment="A", leaderboard=None, brand_sov=None, per_query=None, at="2026-06-14T00:00:00+00:00"):
    return {
        "snapshot_version": "1.0", "captured_at": at, "segment": segment,
        "citation_leaderboard": leaderboard or [], "brand_sov": brand_sov or {}, "per_query": per_query or [],
    }


def _lb(domain, coverage, in_answers=2, auth=0.4, fresh=0.9, total=None, site=None):
    return {"domain": domain, "site_name": site or domain, "in_answers": in_answers,
            "coverage": coverage, "total_citations": total or in_answers,
            "auth_avg": auth, "rel_avg": None, "freshness_avg": fresh}


def _q(query, opportunity, n_citations, brands, theme="主题"):
    return {"query": query, "theme": theme, "opportunity": opportunity, "n_citations": n_citations,
            "named_brands": list(brands), "top_domain": None, "top_site": None, "top_coverage": None, "avg_auth": None}


def test_diff_no_change_is_silent():
    s = _snap(leaderboard=[_lb("a.com", 0.5)], brand_sov={"华为": 1.0}, per_query=[_q("q1", 0.2, 5, ["华为"])])
    d = diff_snapshots(s, s)
    assert d["alerts"] == []
    assert d["citation_changes"]["new_domains"] == []
    assert "无显著变化" in format_alerts(d)


def test_diff_baseline_when_old_none():
    s = _snap(leaderboard=[_lb("a.com", 0.5)])
    d = diff_snapshots(None, s)
    assert d["baseline"] is True and d["alerts"] == []
    assert "基线快照" in format_alerts(d)


def test_diff_new_competitor_domain_alerts_p2():
    old = _snap(leaderboard=[_lb("a.com", 0.5)])
    new = _snap(
        leaderboard=[_lb("a.com", 0.5), _lb("rival.com", 0.33, in_answers=4, total=4, site="对手站")],
        at="2026-06-21T00:00:00+00:00",
    )
    d = diff_snapshots(old, new)
    assert any(x["domain"] == "rival.com" for x in d["citation_changes"]["new_domains"])
    p2 = [a for a in d["alerts"] if a["kind"] == "新对手"]
    assert p2 and p2[0]["level"] == "P2" and "对手站" in p2[0]["msg"]


def test_diff_new_domain_single_answer_not_alerted():
    # 仅出现 1 个答案的新域名（in_answers=1 < 阈值）→ 进 new_domains 但不出告警
    old = _snap(leaderboard=[_lb("a.com", 0.5)])
    new = _snap(leaderboard=[_lb("a.com", 0.5), _lb("blip.com", 0.08, in_answers=1, total=1)], at="2026-06-21T00:00:00+00:00")
    d = diff_snapshots(old, new)
    assert any(x["domain"] == "blip.com" for x in d["citation_changes"]["new_domains"])
    assert [a for a in d["alerts"] if a["kind"] == "新对手"] == []


def test_diff_brand_gap_closed_is_p1_and_ranked_first():
    old = _snap(per_query=[_q("q1", 1.0, 5, [])])  # 旧：品牌空位
    new = _snap(per_query=[_q("q1", 0.0, 5, ["竞品A"])], at="2026-06-21T00:00:00+00:00")  # 新：被点名
    d = diff_snapshots(old, new)
    p1 = [a for a in d["alerts"] if a["level"] == "P1"]
    assert p1 and p1[0]["kind"] == "品牌空位被占" and "竞品A" in p1[0]["msg"]
    assert d["alerts"][0]["level"] == "P1"  # P1 永远排最前


def test_diff_coverage_move_threshold():
    old = _snap(leaderboard=[_lb("a.com", 0.5)])
    near = _snap(leaderboard=[_lb("a.com", 0.58)], at="2026-06-21T00:00:00+00:00")  # +0.08 < 0.10
    assert diff_snapshots(old, near)["citation_changes"]["coverage_moves"] == []
    far = _snap(leaderboard=[_lb("a.com", 0.7)], at="2026-06-21T00:00:00+00:00")  # +0.20 ≥ 0.10
    moves = diff_snapshots(old, far)["citation_changes"]["coverage_moves"]
    assert moves and moves[0]["delta"] == 0.2


def test_diff_freshness_drop_flags_opportunity():
    old = _snap(leaderboard=[_lb("a.com", 0.5, fresh=0.9)])
    new = _snap(leaderboard=[_lb("a.com", 0.5, fresh=0.7)], at="2026-06-21T00:00:00+00:00")  # -0.20
    d = diff_snapshots(old, new)
    assert d["freshness_flags"] and d["freshness_flags"][0]["domain"] == "a.com"
    assert any(a["kind"] == "内容变旧" for a in d["alerts"])


def test_diff_new_brand_appears():
    old = _snap(brand_sov={"华为": 1.0})
    new = _snap(brand_sov={"华为": 0.5, "竞品B": 0.5}, at="2026-06-21T00:00:00+00:00")
    d = diff_snapshots(old, new)
    assert "竞品B" in d["brand_changes"]["new_brands"]
    assert any(a["kind"] == "新品牌" and "竞品B" in a["msg"] for a in d["alerts"])
