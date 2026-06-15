"""冻结假设台账加载/校验：两品类台账齐全 · fail-closed。"""
import pytest

from geo.evolution.assumptions import (
    assumption_by_affected,
    load_assumptions,
    validate_assumptions,
)

_GOOD = {
    "assumption_id": "a",
    "affected_assumption": "geo.x.y",
    "status": "still-holds",
    "description": "d",
    "last_checked": "2026-06-16",
}


def test_both_category_ledgers_load_and_validate_clean():
    for pkg in ("gift_box", "tourism"):
        rows = load_assumptions(pkg)
        assert rows, f"{pkg} 台账为空"
        assert validate_assumptions(rows) == [], f"{pkg} 台账校验有误"
        for r in rows:
            assert r["affected_assumption"]  # 与稳定能力层的连接键非空


def test_validate_empty_failclosed():
    assert validate_assumptions([]) != []  # 空台账≠PASS


def test_validate_bad_status():
    assert any("status" in e for e in validate_assumptions([{**_GOOD, "status": "weird"}]))


def test_validate_duplicate_id():
    assert any("重复" in e for e in validate_assumptions([dict(_GOOD), dict(_GOOD)]))


def test_validate_missing_field():
    bad = {k: v for k, v in _GOOD.items() if k != "affected_assumption"}
    errs = validate_assumptions([bad])
    assert any("affected_assumption" in e for e in errs)


def test_load_missing_ledger_raises():
    with pytest.raises(FileNotFoundError):
        load_assumptions("nonexistent_pkg")


def test_assumption_index_by_affected():
    idx = assumption_by_affected(load_assumptions("tourism"))
    assert "geo.category._PROFILES.tourism.use_search" in idx
