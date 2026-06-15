"""旅游 GEO 分析纯函数测试：景点占答排行 + 内容可赢度。"""
from datetime import datetime, timezone

from geo.evidence.schema import BuyerSegment, Capture
from geo.reporting.tourism import (
    attraction_leaderboard,
    content_winnability,
    opportunity_map,
)


def _cap(query: str, attractions: list[str]) -> Capture:
    ts = datetime(2026, 6, 15, tzinfo=timezone.utc)
    return Capture(
        id=Capture.make_id("doubao", BuyerSegment.A, ts, query + "".join(attractions)),
        engine="doubao",
        query=query,
        buyer_segment=BuyerSegment.A,
        timestamp=ts,
        raw_answer="x",
        named_brands=attractions,  # 引擎通用字段，旅游=景点（按首次出现排序）
    )


def test_attraction_leaderboard_coverage_and_first_choice():
    caps = [
        _cap("q1", ["外滩", "豫园"]),
        _cap("q2", ["外滩", "迪士尼"]),
        _cap("q3", ["豫园", "外滩"]),
    ]
    lb = attraction_leaderboard(caps)
    top = lb[0]
    assert top["attraction"] == "外滩"
    assert top["in_answers"] == 3 and top["coverage"] == 1.0
    assert top["first_choice"] == 2  # q1、q2 排第一
    # 豫园：出现 2 次，首选 1 次（q3）
    yu = next(r for r in lb if r["attraction"] == "豫园")
    assert yu["in_answers"] == 2 and yu["first_choice"] == 1


def test_opportunity_map_marks_empty_as_gap():
    caps = [_cap("纯空位query", []), _cap("有景点query", ["外滩"])]
    rows = {r["query"]: r for r in opportunity_map(caps)}
    assert rows["纯空位query"]["opportunity"] == 1.0
    assert rows["纯空位query"]["n_attractions"] == 0
    assert rows["有景点query"]["opportunity"] == 0.0


def test_content_winnability_gap_scores_highest():
    gap = content_winnability({"opportunity": 1.0, "n_attractions": 0, "non_mega": [], "first": None})
    assert gap["score"] == 90.0 and gap["go"] == "GO"


def test_content_winnability_entrenched_scores_low():
    # 只命中巨头、无长尾 → 难撼动 → 低分观望
    row = {"opportunity": 0.0, "n_attractions": 10, "non_mega": [], "first": "外滩"}
    res = content_winnability(row)
    assert res["go"] == "观望" and res["score"] < 40


def test_content_winnability_thin_longtail_scores_higher():
    # 命中少 + 全是长尾非巨头 → 内容能带长尾进答案 → 高于纯巨头
    row = {"opportunity": 0.0, "n_attractions": 2, "non_mega": ["多伦路", "1933老场坊"], "first": "多伦路"}
    res = content_winnability(row)
    assert res["score"] > 55
