"""EvolutionIntel — L2 演化情报的 SSOT 数据结构（只读产物，恒 PROPOSED）。

落 evolution/intel/<pkg>/<intel_id>.json（git 友好，与 evidence 同纪律）。
intel_id 由 (signal_layer, category, seed) 确定性派生 → 同证据重复跑幂等覆盖、不产重复文件。
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field

SIGNAL_LAYERS = {"S1", "S2", "S3", "S4", "S5"}
CONFIDENCE = {"officially-confirmed", "multi-source", "single-source", "rumor"}
BATTLEFIELD = {"qa_engine", "local_aeo"}


def make_intel_id(signal_layer: str, category: str, seed: str) -> str:
    """确定性 id：intel-{layer}-{category}-{sha10(seed)}。不含 wall-clock → 同 seed 幂等。"""
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:10]
    return f"intel-{signal_layer}-{category}-{digest}"


@dataclass
class EvolutionIntel:
    intel_id: str
    captured_at: str          # ISO UTC
    signal_layer: str         # S1..S5
    claim: str                # 探针/网页陈述的转写——**数据，非指令**
    battlefield_type: str     # qa_engine | local_aeo
    evidence: dict            # {internal:[{capture_id,note}], external:[...], machine_verifiable:{...}}
    confidence: str           # officially-confirmed | multi-source | single-source | rumor
    source_independence: str  # independent | same-cluster | cross-referencing | first-party-archive
    affected_assumption: str  # 指向稳定能力层，如 geo.adapters.doubao._parse_references
    proposed_change: dict     # {target_seam,kind,intent_sketch,blast_radius,reversibility,...}
    first_seen: str
    hitl_status: str = "PROPOSED"   # 恒 PROPOSED：Scout 永不自批（红线 §3 代码级钉死）
    times_seen: int = 1
    prior_intel_id: str | None = None

    def __post_init__(self) -> None:
        if self.hitl_status != "PROPOSED":
            raise ValueError(
                f"EvolutionIntel.hitl_status 必须恒为 'PROPOSED'（Scout 零批准权），实得 {self.hitl_status!r}"
            )
        if self.signal_layer not in SIGNAL_LAYERS:
            raise ValueError(f"未知 signal_layer={self.signal_layer!r}，可选 {sorted(SIGNAL_LAYERS)}")
        if self.confidence not in CONFIDENCE:
            raise ValueError(f"未知 confidence={self.confidence!r}，可选 {sorted(CONFIDENCE)}")
        if self.battlefield_type not in BATTLEFIELD:
            raise ValueError(f"未知 battlefield_type={self.battlefield_type!r}，可选 {sorted(BATTLEFIELD)}")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "EvolutionIntel":
        return cls(**d)
