from geo.reporting.aggregate import competition_level
from geo.reporting.selection import winnability


def test_competition_level():
    assert competition_level(None, None) == "低"
    assert competition_level(0.6, 0.7) == "高"  # 覆盖广 + 权威高
    assert competition_level(0.4, 0.3) == "中"  # 覆盖中
    assert competition_level(0.2, 0.9) == "低"  # 覆盖低


def test_winnability_no_citation_is_watch():
    w = winnability(
        {"n_citations": 0, "avg_auth": None, "named_brands": [], "top_site": None, "top_domain": None}
    )
    assert w["score"] == 20.0 and w["go"] == "观望"


def test_winnability_brand_gap_low_auth_scores_high():
    gap = {"n_citations": 10, "avg_auth": 0.4, "named_brands": [], "top_site": "搜狐", "top_domain": "sohu.com"}
    brand = {**gap, "named_brands": ["华为"]}
    w = winnability(gap)
    # 0.5*(1-0.4) + 0.3*1.0 + 0.2 = 0.8 → 80
    assert w["score"] == 80.0 and w["go"] == "GO"
    # 品牌空位 > 已有品牌
    assert winnability(gap)["score"] > winnability(brand)["score"]
