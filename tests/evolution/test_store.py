"""IntelStore 去抖链（Codex R1 P2）：重复侦查保留 first_seen / 累加 times_seen / 链 prior_intel_id。"""
from geo.evolution.intel import EvolutionIntel
from geo.evolution.store import IntelStore


def _intel(intel_id: str, *, captured_at: str, first_seen: str, times_seen: int = 1,
           assumption: str = "geo.adapters.doubao._parse_references") -> EvolutionIntel:
    return EvolutionIntel(
        intel_id=intel_id,
        captured_at=captured_at,
        signal_layer="S2",
        claim="x",
        battlefield_type="qa_engine",
        evidence={"internal": [], "external": [], "machine_verifiable": {}},
        confidence="single-source",
        source_independence="first-party-archive",
        affected_assumption=assumption,
        proposed_change={"target_seam": "x"},
        first_seen=first_seen,
        times_seen=times_seen,
    )


def test_reconcile_same_id_preserves_first_seen_bumps_times_seen(tmp_path):
    store = IntelStore(tmp_path)
    first = _intel("intel-S2-x-aaaa", captured_at="2026-06-16T00:00:00+00:00",
                   first_seen="2026-06-16T00:00:00+00:00")
    store.save(store.reconcile_history(first))  # 首次：first_seen 原样，times_seen=1

    # 同 id 重复侦查（确定性 id 幂等），新对象 first_seen 是后来的时间
    again = _intel("intel-S2-x-aaaa", captured_at="2026-06-20T00:00:00+00:00",
                   first_seen="2026-06-20T00:00:00+00:00")
    merged = store.reconcile_history(again)
    assert merged.first_seen == "2026-06-16T00:00:00+00:00"  # 保留最早
    assert merged.times_seen == 2                            # 又见一次
    store.save(merged)
    assert store.load("intel-S2-x-aaaa").times_seen == 2


def test_reconcile_chains_prior_for_evolved_signal(tmp_path):
    store = IntelStore(tmp_path)
    old = _intel("intel-S2-x-old0", captured_at="2026-06-16T00:00:00+00:00",
                 first_seen="2026-06-16T00:00:00+00:00", times_seen=3)
    store.save(old)

    # 信号演化：同层同假设但新 seed→新 id
    evolved = _intel("intel-S2-x-new9", captured_at="2026-06-20T00:00:00+00:00",
                     first_seen="2026-06-20T00:00:00+00:00")
    merged = store.reconcile_history(evolved)
    assert merged.prior_intel_id == "intel-S2-x-old0"  # 链到前一条
    assert merged.times_seen == 4                       # 链上累计


def test_find_prior_returns_latest_by_captured_at(tmp_path):
    store = IntelStore(tmp_path)
    # 故意让 hash 序（文件名）与时间序相反：bbbb 更晚但字典序在 zzzz 之前
    store.save(_intel("intel-S2-x-zzzz", captured_at="2026-06-10T00:00:00+00:00",
                      first_seen="2026-06-10T00:00:00+00:00"))
    store.save(_intel("intel-S2-x-bbbb", captured_at="2026-06-18T00:00:00+00:00",
                      first_seen="2026-06-18T00:00:00+00:00"))
    prior = store.find_prior("S2", "geo.adapters.doubao._parse_references")
    assert prior is not None and prior.intel_id == "intel-S2-x-bbbb"  # 按时间取最近，非文件名序


def test_find_prior_excludes_self_and_other_assumptions(tmp_path):
    store = IntelStore(tmp_path)
    store.save(_intel("intel-S2-x-self", captured_at="2026-06-16T00:00:00+00:00",
                      first_seen="2026-06-16T00:00:00+00:00"))
    store.save(_intel("intel-S2-x-othr", captured_at="2026-06-18T00:00:00+00:00",
                      first_seen="2026-06-18T00:00:00+00:00", assumption="some.other.seam"))
    # 排除自身 + 仅匹配同假设 → 无 prior
    assert store.find_prior("S2", "geo.adapters.doubao._parse_references", exclude_id="intel-S2-x-self") is None
