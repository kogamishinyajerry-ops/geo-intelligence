"""S5 候选发现：真证据找到已知良候选 · 排除 watchlist+碎片 · 可回溯子串 · 确定性。"""
from geo.config import get_settings
from geo.evidence.store import EvidenceStore
from geo.evolution.signals.s5_candidates import discover_candidates, extract_candidate_terms
from geo.parsing import extract


def _cands(out):
    return {i.evidence["machine_verifiable"]["candidate"] for i in out}


def test_extract_bold_terms_only():
    terms = extract_candidate_terms("推荐 **外白渡桥** 和 **滨江森林公园**，**ab** 非中文，普通文字不抽")
    assert "外白渡桥" in terms and "滨江森林公园" in terms
    assert "ab" not in terms  # 非 CJK
    assert "普通文字不抽" not in terms  # 未加粗


def test_s5_finds_known_good_candidates():
    # conftest 默认 tourism；真证据应含锁定的良候选
    assert {"外白渡桥", "滨江森林公园"} <= _cands(discover_candidates(min_captures=3))


def test_s5_excludes_watchlist_and_fragments():
    cands = _cands(discover_candidates(min_captures=3))
    assert "东方明珠" not in cands  # watchlist 实体
    assert not any("珠广播电视塔" in c for c in cands)  # 碎片守卫（实测噪声回归钉）
    # 任一候选与任一 watchlist 词条无双向子串关系
    wl = extract.load_watchlist(get_settings().watchlist_path)
    known = set()
    for items in wl.values():
        for it in items or []:
            if isinstance(it, dict):
                for t in [it.get("name"), *(it.get("aliases") or [])]:
                    if t:
                        known.add(t.lower())
    for c in cands:
        cl = c.lower()
        assert not any(cl in k or k in cl for k in known), c


def test_s5_candidates_traceable_to_substrings():
    out = discover_candidates(min_captures=3)
    assert out
    by_id = {c.id: c for c in EvidenceStore(get_settings().evidence_dir).load_all()}
    for i in out:
        mv = i.evidence["machine_verifiable"]
        ids = mv["capture_ids"]
        assert len(ids) >= 3 and mv["occurrences"] == len(ids)
        for cid in ids:
            assert mv["candidate"] in by_id[cid].raw_answer  # 子串确在原文（可回溯）


def test_s5_deterministic_and_proposed():
    a = discover_candidates(min_captures=3)
    b = discover_candidates(min_captures=3)
    assert [i.intel_id for i in a] == [i.intel_id for i in b]  # 同输入同输出（红线#2）
    assert all(i.hitl_status == "PROPOSED" and i.signal_layer == "S5" for i in a)
