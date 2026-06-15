"""旅游 GEO 仪表盘装配层契约测试。

钉死：契约形状 / 每个 opportunity 行带非空 capture_ids 且都内联进 evidence /
leaderboard.kind=="attraction" / 可复现（两次同值，除时间戳）/ render_html 含真值（外滩）。
这些断言保护「可回溯红线」（每个数能回到 capture_id）与「禁编造」（real/mock 照实）。
"""
from __future__ import annotations

from geo.reporting.dashboard_data import build_payload
from geo.reporting.dashboard_render import render_html


def _strip_volatile(payload: dict) -> dict:
    """剔除唯一非确定字段（采集时刻），用于可复现断言。"""
    import copy

    p = copy.deepcopy(payload)
    p["meta"].pop("generated_at", None)
    return p


def test_payload_top_level_contract_shape():
    p = build_payload("A")
    for key in (
        "meta",
        "kpis",
        "leaderboard",
        "sov",
        "opportunity",
        "evidence",
        "monitoring",
        "content_pipeline",
    ):
        assert key in p, f"缺契约顶层字段 {key}"

    meta = p["meta"]
    assert meta["category"] == "tourism"
    assert meta["entity_label"] == "景点"
    assert meta["engine"]  # 非空引擎标签
    assert isinstance(meta["n_captures"], int) and meta["n_captures"] > 0
    # 旅游主战场 = 78 caps（真侦察）
    assert meta["n_captures"] == 78
    assert meta["n_real"] + meta["n_mock"] == meta["n_captures"]

    honesty = meta["honesty"]
    assert honesty["real_engines"], "real_engines 不应为空"
    assert honesty["pending_engines"], "pending_engines 应标注英文侧待 key"
    caveats_blob = " ".join(honesty["caveats"])
    assert "429" in caveats_blob  # 配额墙诚实
    assert "核实" in caveats_blob  # 门票/开放时间发布前核实


def test_kpis_are_telemetry_readouts():
    p = build_payload("A")
    kpis = p["kpis"]
    assert 4 <= len(kpis) <= 6
    for k in kpis:
        assert "label" in k and "value" in k
    labels = [k["label"] for k in kpis]
    assert any("空位" in lbl for lbl in labels)


def test_leaderboard_kind_is_attraction():
    p = build_payload("A")
    lb = p["leaderboard"]
    assert lb["kind"] == "attraction"
    col_keys = {c["key"] for c in lb["columns"]}
    assert {"attraction", "in_answers", "coverage", "first_choice", "first_choice_rate"} <= col_keys
    assert len(lb["rows"]) <= 20
    assert lb["rows"], "排行不应为空"
    # 头部 = 外滩（真值），覆盖 / 首选率为比例（0..1）
    top = lb["rows"][0]
    assert top["attraction"] == "外滩"
    assert 0.0 <= top["coverage"] <= 1.0


def test_sov_descending_and_capped():
    p = build_payload("A")
    sov = p["sov"]
    assert sov, "SoV 不应为空"
    assert len(sov) <= 12
    shares = [row["share"] for row in sov]
    assert shares == sorted(shares, reverse=True)
    # 头部景点应为外滩（真值）
    assert sov[0]["entity"] == "外滩"


def test_every_opportunity_row_has_traceable_capture_ids():
    p = build_payload("A")
    evidence = p["evidence"]
    assert p["opportunity"], "机会图不应为空"
    for o in p["opportunity"]:
        cids = o.get("capture_ids")
        assert cids, f"机会行 {o['query']} 的 capture_ids 为空（违反可回溯红线）"
        for cid in cids:
            assert cid in evidence, f"capture_id {cid} 未内联进 evidence（不可回溯）"


def test_opportunity_contract_fields():
    p = build_payload("A")
    for o in p["opportunity"]:
        for field in ("query", "theme", "segment", "opportunity", "score", "go", "reason", "entities", "top", "capture_ids"):
            assert field in o, f"机会行缺字段 {field}"
        assert len(o["entities"]) <= 6
        # 旅游零联网引用：competition 留空、n_citations=0（诚实）
        assert o["competition"] is None
        assert o["n_citations"] == 0
        top = o["top"]
        assert top is None or ("label" in top and "coverage" in top)


def test_evidence_briefs_honest_about_citations():
    p = build_payload("A")
    assert p["evidence"], "evidence 不应为空"
    for cid, brief in p["evidence"].items():
        for field in ("query", "segment", "engine_model", "timestamp", "is_mock", "raw_excerpt", "named_brands", "cited_sources"):
            assert field in brief, f"证据 {cid} 缺字段 {field}"
        assert isinstance(brief["cited_sources"], list)  # 旅游多为空数组，照实
        assert isinstance(brief["is_mock"], bool)


def test_monitoring_graceful_when_no_history():
    p = build_payload("A")
    mon = p["monitoring"]
    assert "available" in mon and "points" in mon and "note" in mon
    # tourism 现 0 个历史快照 → 不可用 + 诚实 note
    assert mon["available"] is False
    assert mon["note"]


def test_content_pipeline_lists_drafts_pending_review():
    p = build_payload("A")
    pipe = p["content_pipeline"]
    assert pipe, "应列出 content/drafts 草稿"
    for item in pipe:
        assert item["file"].startswith("content/drafts/")
        assert item["title"]
        assert "待审" in item["status"]  # 发布前必人审
        assert "basis" in item


def test_reproducible_except_timestamp():
    a = build_payload("A")
    b = build_payload("A")
    assert _strip_volatile(a) == _strip_volatile(b)


def test_render_html_contains_real_values():
    p = build_payload("A")
    html = render_html(p)
    assert isinstance(html, str) and html
    assert "<!doctype html>" in html.lower()
    # 真值注入：头部景点外滩必须出现在渲染产物里
    assert "外滩" in html
    # 实体语义 = 景点
    assert "景点" in html
