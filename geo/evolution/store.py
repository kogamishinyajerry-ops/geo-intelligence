"""IntelStore — EvolutionIntel 的隔离目录读写（Scout 唯一写权限边界）。

Scout 零写系统配置（watchlist/queries/category/adapter）；只写 evolution/intel/<pkg>/。
路径运行时读 active_profile（不在 import 时锁死品类——共享引擎接缝铁律）。
"""
from __future__ import annotations

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

    def find_prior(self, signal_layer: str, affected_assumption: str) -> EvolutionIntel | None:
        """最近一条同层同假设的 intel（供 times_seen / prior_intel_id 去抖链）。"""
        matches = [
            it for it in self.load_all()
            if it.signal_layer == signal_layer and it.affected_assumption == affected_assumption
        ]
        return matches[-1] if matches else None


def intel_dir_for_active() -> Path:
    """active 品类的 intel 隔离目录：<repo_root>/evolution/intel/<pkg>/。函数内读 profile。"""
    from geo.category import ROOT, active_profile

    return ROOT / "evolution" / "intel" / active_profile().pkg
