"""周期监测 · 编排：snapshot(现有证据) → diff(vs 上次) → 落告警 + 快照 + Notion 队列。

红线遵从：
  • 默认**不花钱**——只对已归档证据建快照并对比；适合 cron 无人值守跑。
  • `--refresh` 会先重跑豆包批量（**花钱**），故被 env `GEO_MONITOR_ALLOW_SPEND=1` 硬门控；
    未授权则拒绝刷新、回退到"仅快照现有证据"，绝不静默花钱（红线：花钱前人审）。
  • 不自动发布到外部；告警先落**本地文件**（truth plane），再排队等人/会话内 MCP 镜像到 Notion。

输出：
  monitoring/history/<seg>-<utc>.json     新快照
  monitoring/alerts/<seg>-<utc>.md         人读告警
  monitoring/ALERTS.md                     滚动追加日志（最新在上）
  monitoring/notion_queue/<seg>-<utc>.json 结构化告警（供会话内推 Notion 控制塔）

退出码：有 P1 告警 → 2；有任意告警 → 1；无变化/基线 → 0（便于 cron/自动化判读）。
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from geo.config import REPO_ROOT
from geo.evidence.schema import BuyerSegment
from geo.monitoring.diff import diff_snapshots, format_alerts
from geo.monitoring.snapshot import (
    build_snapshot,
    latest_snapshot,
    save_snapshot,
)
from geo.reporting.aggregate import load_captures

MON_DIR = REPO_ROOT / "monitoring"
ALERTS_DIR = MON_DIR / "alerts"
QUEUE_DIR = MON_DIR / "notion_queue"
ROLLING_LOG = MON_DIR / "ALERTS.md"


def _stamp(iso: str) -> str:
    return datetime.fromisoformat(iso).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _counts(diff: dict) -> dict:
    c = {"total": 0, "P1": 0, "P2": 0, "P3": 0}
    for a in diff.get("alerts", []):
        c["total"] += 1
        c[a["level"]] = c.get(a["level"], 0) + 1
    return c


def alert_markdown(diff: dict, n_captures: int) -> str:
    """人读告警 .md（纯函数）。"""
    counts = _counts(diff)
    head = f"# GEO 监测告警 · 细分 {diff.get('segment')} · {diff.get('to')}"
    meta = (
        f"- 对比：`{diff.get('from') or '—（基线）'}` → `{diff.get('to')}`\n"
        f"- 证据：{n_captures} captures\n"
        f"- 告警：共 {counts['total']}（P1={counts['P1']} P2={counts['P2']} P3={counts['P3']}）"
    )
    body = format_alerts(diff)
    return f"{head}\n\n{meta}\n\n```\n{body}\n```\n"


def notion_payload(diff: dict, n_captures: int, snapshot_file: str) -> dict:
    """供会话内经 MCP 推 Notion 控制塔的结构化告警（纯函数，不依赖 Notion schema）。"""
    return {
        "segment": diff.get("segment"),
        "captured_at": diff.get("to"),
        "from": diff.get("from"),
        "baseline": diff.get("baseline", False),
        "n_captures": n_captures,
        "counts": _counts(diff),
        "summary": format_alerts(diff),
        "alerts": diff.get("alerts", []),
        "snapshot_file": snapshot_file,
    }


def _exit_code(diff: dict) -> int:
    counts = _counts(diff)
    if counts["P1"]:
        return 2
    if counts["total"]:
        return 1
    return 0


def _maybe_refresh(segment: BuyerSegment, allow_spend: bool) -> None:
    """--refresh：重跑豆包批量（花钱）。未授权则拒绝并回退（红线：花钱前人审）。"""
    if not allow_spend:
        print(
            "⛔ 拒绝自动花钱：未设 GEO_MONITOR_ALLOW_SPEND=1 → 本次仅对【现有证据】建快照，不重新查豆包。\n"
            "   要让监测真正抓取最新答案（产生费用），请显式设 GEO_MONITOR_ALLOW_SPEND=1 后再 --refresh。"
        )
        return
    if segment is not BuyerSegment.A:
        print("ℹ️ 仅 segment A 走真实豆包；其余为 mock，--refresh 跳过。")
        return
    print("💸 GEO_MONITOR_ALLOW_SPEND=1 已授权 → 重跑豆包批量（segment A）…")
    from geo.recon import batch  # 延迟导入：默认路径不触发

    batch.main(["--segment", "A"])


def run(
    segment: BuyerSegment = BuyerSegment.A,
    refresh: bool = False,
    now: datetime | None = None,
) -> dict:
    """监测一轮。返回 diff（含 alerts）。副作用：落快照/告警/队列文件。"""
    allow_spend = os.environ.get("GEO_MONITOR_ALLOW_SPEND") == "1"
    if refresh:
        _maybe_refresh(segment, allow_spend)

    caps = load_captures(segment)
    if not caps:
        print(f"⚠️ 细分 {segment.value} 无证据，跳过。")
        return {"alerts": [], "baseline": True, "segment": segment.value}

    new_snap = build_snapshot(caps, segment.value, now=now)
    prev = latest_snapshot(segment.value)
    diff = diff_snapshots(prev, new_snap)

    snap_path = save_snapshot(new_snap)

    # 告警落地（truth plane）
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _stamp(new_snap["captured_at"])
    md = alert_markdown(diff, len(caps))
    (ALERTS_DIR / f"{segment.value}-{stamp}.md").write_text(md, encoding="utf-8")
    payload = notion_payload(diff, len(caps), snap_path.name)
    (QUEUE_DIR / f"{segment.value}-{stamp}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # 滚动日志（最新在上）
    counts = _counts(diff)
    log_line = (
        f"## {new_snap['captured_at']} · 细分 {segment.value} · "
        f"告警 {counts['total']}（P1={counts['P1']} P2={counts['P2']} P3={counts['P3']}）\n\n"
        f"{format_alerts(diff)}\n\n---\n\n"
    )
    prior = ROLLING_LOG.read_text(encoding="utf-8") if ROLLING_LOG.exists() else "# GEO 监测滚动日志\n\n"
    if prior.startswith("# GEO 监测滚动日志"):
        head, _, rest = prior.partition("\n\n")
        ROLLING_LOG.write_text(f"{head}\n\n{log_line}{rest}", encoding="utf-8")
    else:
        ROLLING_LOG.write_text(f"# GEO 监测滚动日志\n\n{log_line}{prior}", encoding="utf-8")

    print(f"快照 → {snap_path.relative_to(REPO_ROOT)}")
    print(format_alerts(diff))
    print(f"告警 → {(ALERTS_DIR / f'{segment.value}-{stamp}.md').relative_to(REPO_ROOT)}")
    print(f"Notion 队列 → {(QUEUE_DIR / f'{segment.value}-{stamp}.json').relative_to(REPO_ROOT)}")
    return diff


if __name__ == "__main__":
    seg = BuyerSegment.B if "--b" in sys.argv else BuyerSegment.A
    diff = run(segment=seg, refresh="--refresh" in sys.argv)
    sys.exit(_exit_code(diff))
