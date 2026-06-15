"""冻结假设台账（assumptions.yaml）加载/校验。

台账是「系统的自知之明」：每条假设钉 assumption_id + affected_assumption（指向稳定能力层）
+ status（still-holds/at-risk/broken）。它给 Scout 情报一个落点，本身零代码也有价值。
fail-closed：台账缺失/损坏拒绝静默空集（红线 §6）。
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

VALID_STATUS = {"still-holds", "at-risk", "broken"}
_REQUIRED = {"assumption_id", "affected_assumption", "status", "description", "last_checked"}
_ASSUMPTIONS_DIR = Path(__file__).resolve().parent / "ledgers"


def _path_for(pkg: str) -> Path:
    return _ASSUMPTIONS_DIR / f"{pkg}.yaml"


def load_assumptions(pkg: str | None = None) -> list[dict]:
    """加载某品类台账。pkg 缺省时函数内读 active_profile().pkg。台账不存在 → FileNotFoundError（fail-closed）。"""
    if pkg is None:
        from geo.category import active_profile

        pkg = active_profile().pkg
    path = _path_for(pkg)
    if not path.exists():
        raise FileNotFoundError(f"冻结假设台账缺失：{path}（fail-closed，不静默空台账）")
    rows = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(rows, list):
        raise ValueError(f"{path} 顶层必须是 list[假设]，实得 {type(rows).__name__}")
    return rows


def validate_assumptions(rows: list[dict]) -> list[str]:
    """校验台账。返回 error 列表（空=干净）。"""
    errors: list[str] = []
    if not rows:
        return ["❌ 台账为空（空集≠PASS）"]
    seen: set[str] = set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"❌ 第 {i} 条不是 dict：{row!r}")
            continue
        missing = _REQUIRED - set(row)
        if missing:
            errors.append(f"❌ 第 {i} 条缺字段 {sorted(missing)}")
        aid = row.get("assumption_id")
        if aid in seen:
            errors.append(f"❌ assumption_id 重复：{aid!r}")
        if aid is not None:
            seen.add(aid)
        if not row.get("affected_assumption"):
            errors.append(f"❌ {aid!r} 缺 affected_assumption（与稳定能力层的连接键）")
        status = row.get("status")
        if status not in VALID_STATUS:
            errors.append(f"❌ {aid!r} status={status!r} 非法（须 {sorted(VALID_STATUS)}）")
        lc = row.get("last_checked")
        try:
            date.fromisoformat(str(lc))  # 与全仓日期纪律一致（ISO YYYY-MM-DD）
        except (ValueError, TypeError):
            errors.append(f"❌ {aid!r} last_checked={lc!r} 非合法 ISO YYYY-MM-DD")
    return errors


def assumption_by_affected(rows: list[dict]) -> dict[str, dict]:
    return {r["affected_assumption"]: r for r in rows if isinstance(r, dict) and r.get("affected_assumption")}
