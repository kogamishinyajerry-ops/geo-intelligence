"""S2 哨兵：use_search 门控 + 单轮守卫消解误报 · 真骤降产 intel · 真 gift_box 结构断言。"""
import json
from datetime import datetime, timezone

from geo.evidence.schema import BuyerSegment, Capture, CitedSource
from geo.evolution.signals.s2_structure import assert_reference_structure, run_s2


def _raw(searched: bool, n_results: int) -> dict:
    if not searched:
        return {"choices": [{"message": {"content": "x"}}]}
    results = [{"url": f"https://e{i}.com/p", "title": "t"} for i in range(n_results)]
    return {"bot_usage": {"action_details": [{"tool_details": [{"output": {"data": {"data": {"results": results}}}}]}]}}


def _synth_caps(tmp_path, specs):
    """specs: list[(searched, n_results, n_extracted)] → 合成 Capture + raw 文件。"""
    (tmp_path / "raw").mkdir(parents=True, exist_ok=True)
    ts = datetime(2026, 6, 16, tzinfo=timezone.utc)
    caps = []
    for i, (searched, n_results, n_extracted) in enumerate(specs):
        cid = f"doubao-A-20260616T0000{i:02d}Z-{i:010d}"
        (tmp_path / "raw" / f"{cid}.json").write_text(json.dumps(_raw(searched, n_results)), encoding="utf-8")
        caps.append(Capture(
            id=cid, engine="doubao", query=f"q{i}", buyer_segment=BuyerSegment.A,
            timestamp=ts, raw_answer="x", raw_capture_path=f"raw/{cid}.json", is_mock=False,
            cited_sources=[CitedSource(url=f"https://x{j}.com") for j in range(n_extracted)],
        ))
    return caps


def test_assert_structure_searched_with_results():
    s = assert_reference_structure(_raw(True, 10), n_extracted=8)
    assert s["searched"] and s["n_results"] == 10 and s["structure_intact"]


def test_assert_structure_not_searched():
    s = assert_reference_structure(_raw(False, 0), n_extracted=0)
    assert not s["searched"] and not s["structure_intact"]


def test_s2_not_applicable_when_use_search_false():
    # conftest 默认 tourism（use_search=False）→ 零引用是设计基线，绝不报漂移（红色风险回归钉）
    assert run_s2() == []


def test_s2_single_round_all_unsearched_no_false_alarm(monkeypatch, tmp_path):
    monkeypatch.setenv("GEO_CATEGORY", "gift-box")
    caps = _synth_caps(tmp_path, [(False, 0, 0), (False, 0, 0), (False, 0, 0)])
    assert run_s2(caps, baseline_rate=0.9, repo_root=tmp_path) == []  # 全没联网 → 不报机制漂移


def test_s2_healthy_hit_rate_no_alarm(monkeypatch, tmp_path):
    monkeypatch.setenv("GEO_CATEGORY", "gift-box")
    caps = _synth_caps(tmp_path, [(True, 10, 5), (True, 10, 8), (True, 8, 3)])  # 命中率 1.0
    assert run_s2(caps, baseline_rate=0.9, repo_root=tmp_path) == []


def test_s2_real_drop_produces_intel(monkeypatch, tmp_path):
    monkeypatch.setenv("GEO_CATEGORY", "gift-box")
    # 3 条联网但抽到 0 引用 → 命中率 0，基线 0.9，骤降>0.3 → 产 1 条 S2
    caps = _synth_caps(tmp_path, [(True, 10, 0), (True, 10, 0), (True, 8, 0)])
    out = run_s2(caps, baseline_rate=0.9, repo_root=tmp_path)
    assert len(out) == 1
    intel = out[0]
    assert intel.signal_layer == "S2" and intel.hitl_status == "PROPOSED"
    assert intel.proposed_change["requires_codex_review"] is True
    assert intel.evidence["machine_verifiable"]["hit_rate"] == 0.0
    assert len(intel.evidence["internal"]) == 3  # 3 条可回溯 capture_id


def test_s2_min_searched_guard(monkeypatch, tmp_path):
    monkeypatch.setenv("GEO_CATEGORY", "gift-box")
    caps = _synth_caps(tmp_path, [(True, 10, 0), (True, 10, 0)])  # 仅 2 条 < S2_MIN_SEARCHED(3)
    assert run_s2(caps, baseline_rate=0.9, repo_root=tmp_path) == []


def test_s2_structure_on_real_giftbox_raw(monkeypatch):
    monkeypatch.setenv("GEO_CATEGORY", "gift-box")
    from geo.config import get_settings
    from geo.evidence.store import EvidenceStore

    settings = get_settings()
    caps = [c for c in EvidenceStore(settings.evidence_dir).load_all() if not c.is_mock and c.cited_sources]
    assert caps, "需要带引用的真 gift_box 证据"
    c = caps[0]
    raw = json.loads((settings.category_root / c.raw_capture_path).read_text(encoding="utf-8"))
    s = assert_reference_structure(raw, len(c.cited_sources))
    assert s["searched"] and s["n_results"] > 0 and s["structure_intact"]
