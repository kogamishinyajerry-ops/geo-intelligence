"""共享 recon query 类型 + profile 驱动的通用 helper。

ReconQuery（品类无关 dataclass）+ 通用切片函数。具体 query 列表在
`categories.<pkg>.queries.QUERIES`，由 active profile 注入；本模块只提供
对 active profile 的 query 的通用操作。
"""
from __future__ import annotations

from dataclasses import dataclass

from geo.category import active_profile
from geo.evidence.schema import BuyerSegment


@dataclass(frozen=True)
class ReconQuery:
    text: str
    buyer_segment: BuyerSegment
    intent: str = "purchase"
    theme: str = ""


def queries_for_segment(segment: BuyerSegment):
    return [q for q in active_profile().queries if q.buyer_segment == segment]


def phase0_slice():
    """最小切片：1 条 A 段（真跑侧）+ 1 条 B 段（英文/mock 占位，缺则回退 A）。"""
    qs = active_profile().queries
    a = next(q for q in qs if q.buyer_segment == BuyerSegment.A)
    b = next((q for q in qs if q.buyer_segment == BuyerSegment.B), a)
    return {"zh": a, "en": b}
