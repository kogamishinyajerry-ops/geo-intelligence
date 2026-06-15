"""周期监测 · 快照：把当前证据的 GEO 指标冻结成带时间戳的 JSON。

快照是**纯派生物**——每个数字都从已归档 captures 计算，带 capture_ids 可回溯（红线 #1/#2）。
本模块不查 API、不写 Notion；只读证据 → 算指标 → 落 monitoring/history/<seg>-<utc>.json。
对比逻辑见 diff.py。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from geo.config import get_settings
from geo.evidence.schema import BuyerSegment, Capture
from geo.metrics.core import citation_leaderboard, share_of_answer
from geo.reporting.aggregate import load_captures, per_query_rows

SNAPSHOT_VERSION = "1.0"


def _history_dir() -> Path:
    """监测历史目录：按 active 品类的 category_root 运行时解析（合并后在 categories/<cat>/monitoring/）。"""
    return get_settings().category_root / "monitoring" / "history"


def _utc(now: datetime) -> datetime:
    return now.astimezone(timezone.utc)


def _stamp(now: datetime) -> str:
    return _utc(now).strftime("%Y%m%dT%H%M%SZ")


def build_snapshot(captures: list[Capture], segment: str, now: datetime | None = None) -> dict:
    """一组 captures → 快照 dict。纯函数（now 默认取当前 UTC，可注入以便测试/复算）。"""
    now = now or datetime.now(timezone.utc)
    rows = per_query_rows(captures)
    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "captured_at": _utc(now).isoformat(),
        "segment": segment,
        "n_captures": len(captures),
        "capture_ids": sorted(c.id for c in captures),
        "citation_leaderboard": citation_leaderboard(captures),
        "brand_sov": share_of_answer(captures),
        "per_query": [
            {
                "query": r["query"],
                "theme": r["theme"],
                "opportunity": r["opportunity"],
                "n_citations": r["n_citations"],
                "named_brands": r["named_brands"],
                "top_domain": r["top_domain"],
                "top_site": r["top_site"],
                "top_coverage": r["top_coverage"],
                "avg_auth": r["avg_auth"],
            }
            for r in rows
        ],
    }


def save_snapshot(snapshot: dict, history_dir: Path | None = None) -> Path:
    """落盘到 <history>/<segment>-<utc>.json。文件名时间戳取自 snapshot 自身的 captured_at。"""
    history_dir = history_dir or _history_dir()
    history_dir.mkdir(parents=True, exist_ok=True)
    stamp = _stamp(datetime.fromisoformat(snapshot["captured_at"]))
    path = history_dir / f"{snapshot['segment']}-{stamp}.json"
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_snapshot(path: Path | str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def list_snapshots(segment: str, history_dir: Path | None = None) -> list[Path]:
    history_dir = history_dir or _history_dir()
    if not history_dir.exists():
        return []
    return sorted(history_dir.glob(f"{segment}-*.json"))


def latest_snapshot(segment: str, history_dir: Path | None = None) -> dict | None:
    """最近一次快照（按文件名时间戳排序）。无历史则 None。"""
    files = list_snapshots(segment, history_dir)
    return load_snapshot(files[-1]) if files else None


def snapshot_from_evidence(segment: BuyerSegment, now: datetime | None = None) -> dict:
    """从证据库直接构建当前快照（便捷封装：load_captures + build_snapshot）。"""
    caps = load_captures(segment)
    return build_snapshot(caps, segment.value, now=now)


if __name__ == "__main__":
    import sys

    seg = BuyerSegment.B if "--b" in sys.argv else BuyerSegment.A
    snap = snapshot_from_evidence(seg)
    if "--save" in sys.argv:
        p = save_snapshot(snap)
        print(f"已保存快照 → {p}")
    else:
        print(json.dumps(snap, ensure_ascii=False, indent=2))
