"""IntelStore — EvolutionIntel 的隔离目录读写（Scout 唯一写权限边界）。

Scout 零写系统配置（watchlist/queries/category/adapter）；只写 evolution/intel/<pkg>/。
路径运行时读 active_profile（不在 import 时锁死品类——共享引擎接缝铁律）。
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from geo.evolution.intel import EvolutionIntel


class IntelStore:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, intel: EvolutionIntel) -> Path:
        path = self.root / f"{intel.intel_id}.json"
        path.write_text(
            json.dumps(intel.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return path

    def load(self, intel_id: str) -> EvolutionIntel:
        path = self.root / f"{intel_id}.json"
        return EvolutionIntel.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def load_all(self) -> list[EvolutionIntel]:
        return [
            EvolutionIntel.from_dict(json.loads(p.read_text(encoding="utf-8")))
            for p in sorted(self.root.glob("*.json"))
        ]

    def find_prior(self, signal_layer: str, affected_assumption: str,
                   *, exclude_id: str | None = None) -> EvolutionIntel | None:
        """最近一条同层同假设的 intel（供 times_seen / prior_intel_id 去抖链）。
        按 captured_at 取最近一条（load_all 按 intel_id=hash 排序，非时序，故此处显式按时间排）。"""
        matches = [
            it for it in self.load_all()
            if it.signal_layer == signal_layer
            and it.affected_assumption == affected_assumption
            and it.intel_id != exclude_id
        ]
        if not matches:
            return None
        return max(matches, key=lambda it: it.captured_at)

    def reconcile_history(self, intel: EvolutionIntel) -> EvolutionIntel:
        """落盘前对齐去抖链（不可变重建，绝不原地改）。Codex R1 P2：否则重复侦查会重置历史字段。

        • 同 intel_id 已存在（同证据重复侦查，确定性 id 幂等覆盖）
            → 保留旧 first_seen、times_seen+1、沿用旧 prior_intel_id（同一信号又见一次）。
        • 否则若有同层同假设的旧 intel（信号演化、新 seed→新 id）
            → prior_intel_id 指向它、times_seen 累加（链上累计观察次数）。
        • 都没有 → 原样返回（首次出现）。
        """
        same = self.root / f"{intel.intel_id}.json"
        if same.exists():
            old = self.load(intel.intel_id)
            return dataclasses.replace(
                intel,
                first_seen=old.first_seen,
                times_seen=old.times_seen + 1,
                prior_intel_id=old.prior_intel_id,
            )
        prior = self.find_prior(intel.signal_layer, intel.affected_assumption, exclude_id=intel.intel_id)
        if prior is not None:
            return dataclasses.replace(
                intel,
                prior_intel_id=prior.intel_id,
                times_seen=prior.times_seen + 1,
            )
        return intel


def intel_dir_for_active() -> Path:
    """active 品类的 intel 隔离目录：<repo_root>/evolution/intel/<pkg>/。函数内读 profile。"""
    from geo.category import ROOT, active_profile

    return ROOT / "evolution" / "intel" / active_profile().pkg
