"""EvolutionIntel + IntelStore：恒 PROPOSED · 确定性 · 隔离写入。"""
import pytest

from geo.evolution.intel import EvolutionIntel, make_intel_id
from geo.evolution.store import IntelStore


def _mk(**over):
    base = dict(
        intel_id="intel-S5-tourism-abc1234567",
        captured_at="2026-06-16T00:00:00+00:00",
        signal_layer="S5",
        claim="候选「X」复现",
        battlefield_type="qa_engine",
        evidence={"internal": [{"capture_id": "c1", "note": "x"}], "external": [], "machine_verifiable": {}},
        confidence="single-source",
        source_independence="first-party-archive",
        affected_assumption="categories.tourism.config.watchlist",
        proposed_change={"target_seam": "x", "kind": "watchlist-curation"},
        first_seen="2026-06-16T00:00:00+00:00",
    )
    base.update(over)
    return EvolutionIntel(**base)


def test_intel_hitl_status_always_proposed():
    assert _mk().hitl_status == "PROPOSED"
    assert _mk().to_dict()["hitl_status"] == "PROPOSED"
    with pytest.raises(ValueError):
        _mk(hitl_status="APPROVED")  # Scout 零批准权（代码级钉死）


def test_intel_rejects_bad_enums():
    for bad in (dict(signal_layer="S9"), dict(confidence="totally"), dict(battlefield_type="x")):
        with pytest.raises(ValueError):
            _mk(**bad)


def test_intel_roundtrip_and_id_determinism():
    i = _mk()
    assert EvolutionIntel.from_dict(i.to_dict()) == i
    assert make_intel_id("S5", "tourism", "seed") == make_intel_id("S5", "tourism", "seed")
    assert make_intel_id("S5", "tourism", "a") != make_intel_id("S5", "tourism", "b")


def test_intel_store_isolated_roundtrip(tmp_path):
    s = IntelStore(tmp_path / "intel")
    i = _mk()
    p = s.save(i)
    assert p.parent == tmp_path / "intel" and p.name == f"{i.intel_id}.json"
    assert s.load(i.intel_id) == i
    assert s.load_all() == [i]
