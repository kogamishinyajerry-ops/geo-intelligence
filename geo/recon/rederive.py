"""对已存档证据重算 named_brands —— 改 watchlist 后无需重调 API。

体现架构核心（红线 #1/#2）：指标/抽取是对【存档原始证据】的纯函数。
策展 watchlist → 重跑此脚本 → named_brands 重算、证据 id/原文不变。
"""
from __future__ import annotations

import sys

from geo.config import get_settings
from geo.evidence.store import EvidenceStore
from geo.parsing import extract


def rederive_brands() -> int:
    settings = get_settings()
    store = EvidenceStore(settings.evidence_dir)
    watchlist = extract.load_watchlist(settings.watchlist_path)
    caps = store.load_all()
    changed = 0
    for c in caps:
        seg_key = extract.segment_watchlist_key(c.buyer_segment.value)
        new = extract.extract_brands(c.raw_answer, watchlist, seg_key)
        if new != c.named_brands:
            c.named_brands = new
            store.save(c)
            changed += 1
            print(f"  {c.id}  →  {new}")
    print(f"\n重算完成：{len(caps)} captures，更新 {changed} 条 named_brands（原文/证据 id 不变）")
    return 0


if __name__ == "__main__":
    sys.exit(rederive_brands())
