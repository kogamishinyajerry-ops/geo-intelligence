"""Scout CLI：proposal-only（只写隔离 intel 目录）· fail-closed（坏信号/坏台账拒跑）。"""
import geo.evolution.assumptions as assumptions_mod
import geo.evolution.store as store_mod
from geo.evolution import scout


def test_scout_unknown_signal_failclosed():
    assert scout.main(["--signals", "s9"]) == 2  # 未知信号 → 非零退出


def test_scout_proposal_only_writes_only_intel(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(store_mod, "intel_dir_for_active", lambda: tmp_path / "intel")
    assert scout.main(["--signals", "s5"]) == 0
    assert list((tmp_path / "intel").glob("*.json"))  # intel 落隔离目录
    out = capsys.readouterr().out
    assert "proposal-only" in out and "PROPOSED" in out


def test_scout_dry_run_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(store_mod, "intel_dir_for_active", lambda: tmp_path / "intel")
    assert scout.main(["--signals", "s5", "--dry-run"]) == 0
    assert not (tmp_path / "intel").exists()  # dry-run 绝不落盘


def test_scout_fail_closed_on_bad_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(store_mod, "intel_dir_for_active", lambda: tmp_path / "intel")
    monkeypatch.setattr(assumptions_mod, "validate_assumptions", lambda rows: ["❌ bad ledger"])
    assert scout.main(["--signals", "s5"]) == 2  # 坏台账拒跑
    assert not (tmp_path / "intel").exists()  # 不写任何 intel
