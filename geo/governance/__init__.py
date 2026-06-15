"""统一 Red-line Gate（治理脊柱）。

任何「要落地/对外的产物」+ 任何「改红线 / 改 watchlist / 加 adapter 的提案」落地前的
统一机器门。**机器可拒不可批**：Gate 只返回 PASS/FAIL，批准是 HITL（人）的事。fail-closed。
"""
from geo.governance.gate import (
    KIND_ADAPTER,
    KIND_SCHEMA,
    KIND_WATCHLIST,
    GateResult,
    GateValidatorError,
    check,
)

__all__ = [
    "check",
    "GateResult",
    "GateValidatorError",
    "KIND_SCHEMA",
    "KIND_WATCHLIST",
    "KIND_ADAPTER",
]
