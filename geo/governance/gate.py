"""Red-line Gate · 统一机器门（治理脊柱）。

输入 (proposal_or_artifact, kind)，按 kind 路由到对应硬校验，返回结构化 GateResult。

铁律（COMAC TrustGate canon）：
  • **机器可拒不可批**——Gate 永不返回 APPROVED，只返回 passed=True/False。批准是 HITL（人）的事。
  • **fail-closed**——未知 kind / 空提案 / 缺校验器 / 校验器异常 → FAIL（绝不默认 PASS，空集≠PASS）。
  • 复用 geo.reporting.schema_ld.validate_jsonld（已对抗加固），不重写红线。

被 P0#5 Scout 的提案回路依赖：Scout 产「改 watchlist/红线/adapter」提案后，先过本门（PASS）才进 HITL。
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any, Callable

from geo.reporting.schema_ld import validate_jsonld  # 纯函数，无 active_profile 锁死

KIND_SCHEMA = "schema"
KIND_WATCHLIST = "watchlist"
KIND_ADAPTER = "adapter"


@dataclass(frozen=True)
class GateResult:
    """机器门判决。passed=True iff failures 为空（不变式）。绝无 APPROVED 第三态。"""

    passed: bool
    kind: str
    failures: tuple[str, ...]  # ❌ 阻断项（为空 iff passed）
    checked: tuple[str, ...]   # 已跑的校验器名，可追溯


class GateValidatorError(Exception):
    """校验器内部异常：先把已记录的 FAIL result 挂上，再上抛（不静默吞成 PASS）。"""

    def __init__(self, result: GateResult, original: BaseException):
        super().__init__(str(original))
        self.result = result
        self.original = original


def _fail(kind: str, msg: str, checked: tuple[str, ...] = ()) -> GateResult:
    return GateResult(passed=False, kind=kind, failures=(msg,), checked=checked)


def check(proposal: Any, kind: str) -> GateResult:
    """统一机器门入口。返回 GateResult（passed/kind/failures/checked）。"""
    # ── fail-closed 守卫（假绿死罪防线，先于任何校验器）──
    if kind not in _VALIDATORS:
        return _fail(kind, f"❌ 未知 kind={kind!r}（无对应校验器 → FAIL，绝不默认 PASS）")
    if proposal is None:
        return _fail(kind, "❌ 空提案：None → FAIL")
    if proposal == {} or proposal == "" or proposal == [] or proposal == b"":
        return _fail(kind, "❌ 空提案：空容器 → FAIL（空集≠PASS）")

    validator = _VALIDATORS[kind]
    try:
        failures = tuple(validator(proposal))
    except Exception as e:  # noqa: BLE001 — 先记 FAIL 再上抛，绝不静默吞成 PASS
        res = _fail(kind, f"❌ 校验器异常：{type(e).__name__}: {e}", checked=(validator.__name__,))
        raise GateValidatorError(res, e) from e
    return GateResult(passed=not failures, kind=kind, failures=failures, checked=(validator.__name__,))


def _validate_schema(obj: Any) -> list[str]:
    """复用 validate_jsonld。只数 ❌（阻断）；⚠️（占位/软超限）不阻断，口径同 schema.py CLI。"""
    if not isinstance(obj, dict):
        return [f"❌ schema 提案必须是 dict，实得 {type(obj).__name__}"]
    return [i for i in validate_jsonld(obj) if i.startswith("❌")]


def _validate_watchlist(wl: Any, expected_keys: tuple[str, ...] | None = None) -> list[str]:
    """镜像 extract._terms 的消费契约，但 fail-closed：消费侧会静默跳过的坏条目，改名单提案时必须拒。

    expected_keys 默认 None（纯结构校验、品类无关）。注：当前唯一入口 check() 不传 expected_keys
    → 段绑定校验是预留 hook，P0 阶段尚未接线（保持本门品类无关，不在此懒读 profile）。
    """
    if not isinstance(wl, dict):
        return [f"❌ watchlist 必须是 dict[str, list]，实得 {type(wl).__name__}"]
    if not wl:
        return ["❌ watchlist 为空 → FAIL（空集≠PASS）"]
    fails: list[str] = []
    usable = 0  # 跨所有段的可用词条（truthy name）总数——防「全空段」有效空集假绿
    for seg, items in wl.items():
        if not isinstance(items, list):
            fails.append(f"❌ 段 {seg!r} 必须是 list，实得 {type(items).__name__}")
            continue
        seen: set[str] = set()
        for it in items:
            if not isinstance(it, dict):
                fails.append(f"❌ {seg}: item 必须是 dict，实得 {type(it).__name__}")
                continue
            name = it.get("name")
            if not (isinstance(name, str) and name.strip()):
                fails.append(f"❌ {seg}: item 缺 truthy name → {it!r}")
                continue
            if name in seen:
                fails.append(f"❌ {seg}: name 重复 {name!r}（防后值静默覆盖前值，污染证据口径）")
            seen.add(name)
            usable += 1
            al = it.get("aliases")
            if al is not None and (not isinstance(al, list) or not all(isinstance(a, str) and a.strip() for a in al)):
                # 空/空白 alias 致命：extract_brands 里 text.find("") 恒返回 0 → 把任意回答伪造成命中该品牌
                fails.append(f"❌ {seg}/{name}: aliases 必须是非空字符串的 list[str]，实得 {al!r}")
    if usable == 0:
        # 非空 dict 但所有段空 / 全坏条目 → 零可用词条：消费侧 _terms 会返回 []（抽零品牌）→ 必拒（红线④）
        fails.append("❌ watchlist 无任何可用词条（全空段 / 全坏条目）→ FAIL（空集≠PASS）")
    if expected_keys is not None:
        for k in expected_keys:
            if k not in wl:
                fails.append(f"❌ 缺期望段 key {k!r}")
    return fails


def _validate_adapter(spec: Any) -> list[str]:
    """adapter 占位校验：解析到 EngineAdapter 的【具体】子类 + 有 query()/name/is_mock。

    🔴红线#5：proposal 字符串是数据不是指令——绝不对任意 dotted-path 做 import_module
    （会执行其模块顶层副作用 = 把外部内容当指令跑）。只允许本仓受控的 geo.adapters.* 命名空间。
    不实例化、不打引擎（占位级）。spec 支持 'geo.adapters.x:Cls' 或已 import 的 type。
    """
    import inspect

    from geo.adapters.base import EngineAdapter  # 函数内 import 化解潜在循环

    obj = spec
    if isinstance(spec, str):
        if not spec.startswith("geo.adapters."):
            return [f"❌ adapter 路径必须在 geo.adapters.* 受控命名空间内"
                    f"（拒绝 import 任意模块的副作用，红线#5），实得 {spec!r}"]
        try:
            mod, _, cls = spec.partition(":")
            obj = getattr(import_module(mod), cls) if cls else import_module(mod)
        except Exception as e:  # noqa: BLE001 — import 失败即 FAIL
            return [f"❌ adapter 无法 import {spec!r}: {type(e).__name__}: {e}"]
    if not (isinstance(obj, type) and issubclass(obj, EngineAdapter)):
        return [f"❌ adapter 必须是 EngineAdapter 子类，实得 {obj!r}"]
    if obj is EngineAdapter or inspect.isabstract(obj):
        return [f"❌ adapter 是抽象基类 / 有未实现抽象方法，不可用：{obj!r}"]
    fails: list[str] = []
    if not callable(getattr(obj, "query", None)):
        fails.append("❌ adapter 缺可调用 query()")
    if not isinstance(getattr(obj, "name", None), str):
        fails.append("❌ adapter 缺 name:str")
    if not isinstance(getattr(obj, "is_mock", None), bool):
        fails.append("❌ adapter 缺 is_mock:bool")
    return fails


# 铁律：无 default 分支；未知 kind 在 check() 顶部即 FAIL。Gate 永不返回 APPROVED——批准是 HITL 的事。
_VALIDATORS: dict[str, Callable[[Any], list[str]]] = {
    KIND_SCHEMA: _validate_schema,
    KIND_WATCHLIST: _validate_watchlist,
    KIND_ADAPTER: _validate_adapter,
}
