from datetime import datetime, timezone

from geo.evidence.schema import BuyerSegment, Capture, CitedSource
from geo.metrics.core import (
    citation_leaderboard,
    first_choice_rate,
    mention_rate,
    opportunity_score,
    share_of_answer,
)

_TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _cap(brands: list[str]) -> Capture:
    raw = " ".join(brands) or "generic answer, no brand"
    return Capture(
        id=Capture.make_id("t", "B", _TS, raw),
        engine="t",
        query="q",
        buyer_segment=BuyerSegment.B,
        timestamp=_TS,
        raw_answer=raw,
        named_brands=list(brands),
    )


def test_mention_rate():
    caps = [_cap(["A", "B"]), _cap(["A"]), _cap([])]
    assert mention_rate(caps, "A") == 2 / 3
    assert mention_rate(caps, "B") == 1 / 3
    assert mention_rate([], "A") == 0.0


def test_share_of_answer():
    caps = [_cap(["A", "B"]), _cap(["A"])]
    sov = share_of_answer(caps)
    assert sov == {"A": 2 / 3, "B": 1 / 3}
    assert share_of_answer([_cap([])]) == {}


def test_first_choice_rate():
    caps = [_cap(["A", "B"]), _cap(["B", "A"]), _cap([])]
    assert first_choice_rate(caps, "A") == 1 / 3
    assert first_choice_rate(caps, "B") == 1 / 3


def test_opportunity_score():
    assert opportunity_score([_cap([]), _cap(["A"]), _cap([])]) == 2 / 3
    assert opportunity_score([]) == 0.0
    assert opportunity_score([_cap(["A"])]) == 0.0


def _cap_cited(sources):
    """sources: list of (domain, site_name, auth_score)。"""
    cs = [
        CitedSource(url=f"https://{d}/p", domain=d, site_name=sn, auth_score=a)
        for (d, sn, a) in sources
    ]
    return Capture(
        id=Capture.make_id("t", "B", _TS, repr(sources)),
        engine="t", query="q", buyer_segment=BuyerSegment.B, timestamp=_TS,
        raw_answer="x", cited_sources=cs,
    )


def test_citation_leaderboard():
    caps = [
        _cap_cited([("a.com", "SiteA", 0.5), ("a.com", "SiteA", 0.5), ("b.com", "SiteB", 0.3)]),
        _cap_cited([("a.com", "SiteA", 0.7)]),
    ]
    lb = citation_leaderboard(caps)
    assert lb[0]["domain"] == "a.com"
    assert lb[0]["in_answers"] == 2  # 出现在 2 个 answer
    assert lb[0]["total_citations"] == 3  # 总被引 3 次
    assert lb[0]["coverage"] == 1.0  # 2/2
    assert lb[0]["auth_avg"] == round((0.5 + 0.5 + 0.7) / 3, 3)
    b = next(r for r in lb if r["domain"] == "b.com")
    assert b["in_answers"] == 1 and b["coverage"] == 0.5
    assert citation_leaderboard([]) == []
