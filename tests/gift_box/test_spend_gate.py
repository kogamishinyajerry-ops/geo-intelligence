"""P0#3 花钱闸覆盖：require_spend 守住所有真打付费引擎的入口；mock 路径绝不被门控；fail-closed。

设计：blocked 路径在 require_spend 处即抛、早于任何网络/写盘；mock 路径用 tmp evidence 隔离写入。
"""
import pytest

from geo.config import (
    SPEND_ENV,
    SpendNotAuthorizedError,
    get_settings,
    require_spend,
    spend_allowed,
)


# ── config 级：纯函数，零副作用 ──

def test_spend_allowed_strict_equality(monkeypatch):
    monkeypatch.delenv(SPEND_ENV, raising=False)
    assert spend_allowed() is False
    for v in ("true", "TRUE", "yes", "0", "", " 1 "):
        monkeypatch.setenv(SPEND_ENV, v)
        assert spend_allowed() is False, f"{v!r} 不应放行（fail-closed）"
    monkeypatch.setenv(SPEND_ENV, "1")
    assert spend_allowed() is True


def test_require_spend_raises_when_not_authorized(monkeypatch):
    monkeypatch.delenv(SPEND_ENV, raising=False)
    with pytest.raises(SpendNotAuthorizedError) as ei:
        require_spend()
    assert SPEND_ENV in str(ei.value) and "花钱" in str(ei.value)


def test_require_spend_passes_when_authorized(monkeypatch):
    monkeypatch.setenv(SPEND_ENV, "1")
    assert require_spend() is None


def test_missing_spend_vs_missing_creds_distinguished(monkeypatch):
    # 缺花钱许可（凭证齐）→ SpendNotAuthorizedError；花钱已授权+缺凭证 → require_ark 的 RuntimeError（非 Spend...）
    monkeypatch.delenv(SPEND_ENV, raising=False)
    with pytest.raises(SpendNotAuthorizedError):
        require_spend()
    monkeypatch.setenv(SPEND_ENV, "1")
    require_spend()  # 已授权，不抛
    s = get_settings().model_copy(update={"ark_api_key": None, "ark_model": None})
    with pytest.raises(RuntimeError) as ei:
        s.require_ark()
    assert not isinstance(ei.value, SpendNotAuthorizedError)
    assert "ARK_API_KEY" in str(ei.value)


# ── 入口级：花钱闸真接在真打路径上；mock 路径绝不被门控 ──

@pytest.fixture
def _tmp_pipeline(tmp_path, monkeypatch):
    """把 recon 入口的 get_settings 重指到 tmp evidence，避免污染真证据；watchlist 仍用真名单。"""
    tmp_settings = get_settings().model_copy(
        update={"category_root": tmp_path, "evidence_dir": tmp_path / "evidence"}
    )
    import geo.recon.batch as recon_batch
    import geo.recon.run as recon_run

    monkeypatch.setattr(recon_batch, "get_settings", lambda: tmp_settings)
    monkeypatch.setattr(recon_run, "get_settings", lambda: tmp_settings)
    return tmp_path


def test_batch_real_segment_blocked_without_spend(monkeypatch):
    from geo.adapters.doubao import DoubaoAdapter
    from geo.recon import batch

    monkeypatch.delenv(SPEND_ENV, raising=False)
    monkeypatch.setenv("ARK_API_KEY", "x")  # 凭证齐 → 证明拦的是花钱许可，非凭证
    monkeypatch.setenv("ARK_MODEL", "m")
    monkeypatch.setattr(DoubaoAdapter, "query", lambda *a, **k: pytest.fail("真打路径不应被触达"))
    assert batch.main(["--segment", "A"]) == 2  # A=real 段，花钱被拒 → 非零退出


def test_batch_mock_segment_not_gated(_tmp_pipeline, monkeypatch):
    from geo.recon import batch

    monkeypatch.delenv(SPEND_ENV, raising=False)
    monkeypatch.delenv("ARK_API_KEY", raising=False)
    calls = []
    real_require = batch.require_spend
    monkeypatch.setattr(batch, "require_spend", lambda: (calls.append(1), real_require())[1])
    assert batch.main(["--segment", "B"]) == 0  # B=mock 段，不受门控
    assert calls == []  # mock 段从不调花钱闸


def test_phase0_blocked_without_spend(monkeypatch):
    from geo.adapters.doubao import DoubaoAdapter
    from geo.recon import run as recon_run

    monkeypatch.delenv(SPEND_ENV, raising=False)
    monkeypatch.setenv("ARK_API_KEY", "x")
    monkeypatch.setenv("ARK_MODEL", "m")
    monkeypatch.setattr(DoubaoAdapter, "query", lambda *a, **k: pytest.fail("真打路径不应被触达"))
    assert recon_run.main(["--phase0"]) == 2


def test_mock_only_not_gated(_tmp_pipeline, monkeypatch):
    from geo.recon import run as recon_run

    monkeypatch.delenv(SPEND_ENV, raising=False)
    monkeypatch.delenv("ARK_API_KEY", raising=False)
    assert recon_run.main(["--mock-only"]) == 0  # 全 mock，零花钱，不受门控
