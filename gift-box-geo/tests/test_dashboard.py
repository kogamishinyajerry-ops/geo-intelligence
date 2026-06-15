"""仪表盘装配层契约测试 —— 形状符合数据契约 / 数字可回溯 / 可复现 / 渲染含真值。

红线守护：每个 opportunity 行的 capture_ids 非空且都内联进 evidence（可回溯）；
n_captures 等于真实证据数；两次调用除 generated_at 外完全相等（可复现）；
render_html(build_payload()) 产出含真值字符串的 HTML（assembler↔render 接缝活）。
"""
from __future__ import annotations

import copy

from geo.reporting.aggregate import load_captures
from geo.reporting.dashboard_data import build_payload
from geo.reporting.dashboard_render import render_html


def test_payload_shape_matches_contract():
    p = build_payload()
    # 顶层键齐全
    for key in (
        "meta", "kpis", "leaderboard", "sov",
        "opportunity", "evidence", "monitoring", "content_pipeline",
    ):
        assert key in p, f"缺顶层键 {key}"

    meta = p["meta"]
    for key in (
        "category", "title", "subtitle", "entity_label", "engine",
        "engine_models", "generated_at", "n_captures", "n_real", "n_mock",
        "n_queries", "segments", "evidence_dir", "honesty",
    ):
        assert key in meta, f"meta 缺键 {key}"
    assert meta["category"] == "gift-box"
    assert meta["entity_label"] == "品牌"

    honesty = meta["honesty"]
    assert "豆包（火山方舟，中文侧）" in honesty["real_engines"]
    assert any("Perplexity" in e for e in honesty["pending_engines"])
    # caveats 至少含两条钦定局限
    caveats = "".join(honesty["caveats"])
    assert "商品卡" in caveats and "触发" in caveats

    # kpis：4-6 个遥测读数，每个有 label/value
    assert 4 <= len(p["kpis"]) <= 6
    for k in p["kpis"]:
        assert "label" in k and "value" in k


def test_n_captures_equals_real_count():
    p = build_payload()
    caps = load_captures()
    n = len(caps)
    assert p["meta"]["n_captures"] == n
    n_mock = sum(1 for c in caps if c.is_mock)
    assert p["meta"]["n_mock"] == n_mock
    assert p["meta"]["n_real"] == n - n_mock


def test_leaderboard_kind_is_citation():
    p = build_payload()
    lb = p["leaderboard"]
    assert lb["kind"] == "citation"
    assert len(lb["rows"]) <= 15
    # columns 形状（key/label/fmt）
    for c in lb["columns"]:
        assert "key" in c and "label" in c and "fmt" in c
    # 每行带契约要求的 citation 字段
    if lb["rows"]:
        r0 = lb["rows"][0]
        for key in ("domain", "in_answers", "coverage", "total_citations", "auth_avg"):
            assert key in r0


def test_sov_descending_and_capped():
    p = build_payload()
    sov = p["sov"]
    assert len(sov) <= 10
    shares = [s["share"] for s in sov]
    assert shares == sorted(shares, reverse=True), "SoV 必须降序"
    for s in sov:
        assert "entity" in s and "share" in s


def test_opportunity_capture_ids_nonempty_and_traceable():
    """每个机会行有非空 capture_ids，且这些 id 都内联进 evidence（可回溯红线）。"""
    p = build_payload()
    opp = p["opportunity"]
    assert opp, "机会图不应为空（segment A 有真数据）"
    evidence = p["evidence"]
    for o in opp:
        assert o["capture_ids"], f"机会行 capture_ids 为空：{o['query']}"
        for cid in o["capture_ids"]:
            assert cid in evidence, f"capture_id {cid} 未内联进 evidence（不可回溯）"


def test_evidence_brief_shape():
    p = build_payload()
    evidence = p["evidence"]
    assert evidence, "evidence 不应为空"
    for cid, brief in evidence.items():
        for key in (
            "query", "segment", "engine_model", "timestamp",
            "is_mock", "raw_excerpt", "named_brands", "cited_sources",
        ):
            assert key in brief, f"evidence[{cid}] 缺键 {key}"
        assert len(brief["raw_excerpt"]) <= 280
        assert len(brief["named_brands"]) <= 10
        assert len(brief["cited_sources"]) <= 5


def test_content_pipeline_basis_no_fabrication():
    """内容流水线：每条有 file/title/status/basis；匹配不到 query 时 capture_ids 为空（不编造）。"""
    p = build_payload()
    for item in p["content_pipeline"]:
        for key in ("file", "title", "status", "basis"):
            assert key in item
        assert "待审" in item["status"]
        basis = item["basis"]
        assert "capture_ids" in basis
        # basis 的 capture_ids（若非空）必须可回溯进 evidence
        for cid in basis["capture_ids"]:
            assert cid in p["evidence"]


def test_monitoring_shape():
    p = build_payload()
    mon = p["monitoring"]
    assert "available" in mon and "points" in mon and "note" in mon
    for pt in mon["points"]:
        for key in ("captured_at", "top_label", "top_coverage", "n_captures"):
            assert key in pt


def test_reproducible_except_generated_at():
    """同输入两次调用，除 meta.generated_at 外 payload 完全相等（可复现红线）。"""
    p1 = build_payload()
    p2 = build_payload()
    a = copy.deepcopy(p1)
    b = copy.deepcopy(p2)
    a["meta"].pop("generated_at")
    b["meta"].pop("generated_at")
    assert a == b, "除 generated_at 外 payload 应完全可复现"


def test_render_html_contains_real_values():
    """render_html(build_payload()) 产出 HTML，含来自真实 captures 的真值字符串。"""
    p = build_payload()
    html = render_html(p)
    assert html.startswith("<!doctype html>")
    # 头号 incumbent 站点名（真实证据派生）须出现在 HTML 数据里
    assert "信尚礼品" in html
    # 标题真值
    assert p["meta"]["title"] in html
    # 至少一个真实 capture_id 进了 HTML
    some_cid = next(iter(p["evidence"]))
    assert some_cid in html
