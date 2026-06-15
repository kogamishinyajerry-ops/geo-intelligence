"""P0#4 Red-line Gate 统一机器门：fail-closed + 机器可拒不可批 + 复用 validate_jsonld。"""
import pytest

from geo.governance import (
    KIND_ADAPTER,
    KIND_SCHEMA,
    KIND_WATCHLIST,
    GateResult,
    GateValidatorError,
    check,
)

_CLEAN_ARTICLE = {
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "上海小众亲子景点实用整理",
    "description": "一段中性的短摘要，介绍几个适合带孩子的去处。",
    "datePublished": "2026-06-16",
}


# ── schema kind（复用 validate_jsonld，只 ❌ 阻断，⚠️ 不阻断）──

def test_gate_passes_clean_schema_artifact():
    r = check(_CLEAN_ARTICLE, KIND_SCHEMA)
    assert r.passed is True and r.failures == ()
    assert "_validate_schema" in r.checked


def test_gate_fails_schema_with_ad_term():
    r = check({**_CLEAN_ARTICLE, "description": "限时优惠扫码加微信"}, KIND_SCHEMA)
    assert r.passed is False and any("广告" in f for f in r.failures)


def test_gate_fails_schema_non_dict():
    r = check("not a dict", KIND_SCHEMA)
    assert r.passed is False and any("必须是 dict" in f for f in r.failures)


# ── watchlist kind ──

def test_gate_passes_real_watchlist_yaml():
    from geo.category import active_profile
    from geo.parsing import extract

    wl = extract.load_watchlist(active_profile().root / "config" / "watchlist.yaml")
    r = check(wl, KIND_WATCHLIST)
    assert r.passed is True, r.failures


def test_gate_fails_watchlist_item_not_dict():
    r = check({"segA": ["裸字符串"]}, KIND_WATCHLIST)
    assert r.passed is False and any("item 必须是 dict" in f for f in r.failures)


def test_gate_fails_watchlist_missing_name():
    r = check({"segA": [{"aliases": ["x"]}]}, KIND_WATCHLIST)
    assert r.passed is False and any("缺 truthy name" in f for f in r.failures)


def test_gate_fails_watchlist_duplicate_name():
    r = check({"segA": [{"name": "华为"}, {"name": "华为"}]}, KIND_WATCHLIST)
    assert r.passed is False and any("name 重复" in f for f in r.failures)


def test_gate_fails_watchlist_bad_aliases():
    r = check({"segA": [{"name": "x", "aliases": "notalist"}]}, KIND_WATCHLIST)
    assert r.passed is False and any("aliases 必须是" in f and "list" in f for f in r.failures)


def test_gate_fails_watchlist_all_empty_segments():
    # 非空 dict 但所有段空 list → 零可用词条 = 有效空集 → 必须 FAIL（fail-open 死罪防线）
    assert check({"segA": []}, KIND_WATCHLIST).passed is False
    r = check({"segA": [], "segB": []}, KIND_WATCHLIST)
    assert r.passed is False and any("无任何可用词条" in f for f in r.failures)


# ── adapter kind（可 import 占位，不实例化不打引擎）──

def test_gate_passes_adapter_by_dotted_path():
    assert check("geo.adapters.doubao:DoubaoAdapter", KIND_ADAPTER).passed is True
    assert check("geo.adapters.mock:MockAdapter", KIND_ADAPTER).passed is True


def test_gate_fails_adapter_bad_path():
    r = check("geo.adapters.nope:Ghost", KIND_ADAPTER)
    assert r.passed is False and any("无法 import" in f for f in r.failures)


def test_gate_fails_adapter_not_subclass():
    r = check("geo.adapters.base:RawResult", KIND_ADAPTER)
    assert r.passed is False and any("EngineAdapter 子类" in f for f in r.failures)


def test_gate_fails_adapter_arbitrary_import_blocked():
    # 红线#5：命名空间外的 dotted-path 在 import 之前即 FAIL（绝不执行 'this'/'os' 的顶层副作用）
    for bad in ("this", "os:getcwd", "subprocess"):
        r = check(bad, KIND_ADAPTER)
        assert r.passed is False and any("命名空间" in f for f in r.failures), bad


def test_gate_fails_adapter_abstract_base():
    from geo.adapters.base import EngineAdapter
    assert check("geo.adapters.base:EngineAdapter", KIND_ADAPTER).passed is False  # 抽象基类不可用
    assert check(EngineAdapter, KIND_ADAPTER).passed is False


def test_gate_fails_watchlist_empty_alias():
    # 空/空白 alias → extract_brands 里 text.find("")==0 把任意回答伪造成命中 → 必 FAIL
    assert check({"segA": [{"name": "B", "aliases": [""]}]}, KIND_WATCHLIST).passed is False
    assert check({"segA": [{"name": "B", "aliases": ["  "]}]}, KIND_WATCHLIST).passed is False


# ── fail-closed 守卫（假绿死罪防线）──

def test_failclosed_unknown_kind():
    r = check({"@type": "Article"}, "totally-unknown")
    assert r.passed is False and any("未知 kind" in f for f in r.failures)


@pytest.mark.parametrize("kind", [KIND_SCHEMA, KIND_WATCHLIST, KIND_ADAPTER])
def test_failclosed_empty_proposal(kind):
    for empty in ({}, "", []):
        r = check(empty, kind)
        assert r.passed is False and any("空提案" in f for f in r.failures)


def test_failclosed_none_proposal():
    r = check(None, KIND_SCHEMA)
    assert r.passed is False and any("空提案" in f for f in r.failures)


def test_validator_exception_records_fail_then_raises(monkeypatch):
    import geo.governance.gate as gate

    def boom(_):
        raise RuntimeError("boom")

    monkeypatch.setitem(gate._VALIDATORS, KIND_SCHEMA, boom)
    with pytest.raises(GateValidatorError) as ei:
        check({"@type": "Article"}, KIND_SCHEMA)
    assert ei.value.result.passed is False
    assert any("校验器异常" in f and "RuntimeError" in f for f in ei.value.result.failures)


# ── 铁律：机器可拒不可批（永不 APPROVED）──

def test_gate_never_returns_approved():
    fields = set(GateResult.__dataclass_fields__)
    assert fields == {"passed", "kind", "failures", "checked"}
    assert not any("approv" in f.lower() for f in fields)
    assert isinstance(check(_CLEAN_ARTICLE, KIND_SCHEMA).passed, bool)  # 仅 PASS/FAIL，无第三态


def test_gate_result_invariant_passed_iff_no_failures():
    cases = [
        (_CLEAN_ARTICLE, KIND_SCHEMA),
        ({**_CLEAN_ARTICLE, "description": "限时抢购"}, KIND_SCHEMA),
        ("geo.adapters.mock:MockAdapter", KIND_ADAPTER),
        ({"segA": [{"name": "x"}]}, KIND_WATCHLIST),
    ]
    for proposal, kind in cases:
        r = check(proposal, kind)
        assert r.passed == (len(r.failures) == 0)
