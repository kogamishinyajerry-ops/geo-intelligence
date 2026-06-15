#!/usr/bin/env bash
# Lily GEO · 每周监测（本地 cron 调用）
# ───────────────────────────────────────────────────────────────────────
# 默认**不花钱**：未设 GEO_MONITOR_ALLOW_SPEND=1 时，--refresh 会被拒绝，
#   退回到"仅对现有证据建快照 + 对比上次"。安全、可无人值守。
# 要让每周真正重查豆包（**产生费用**）→ 取消下方 `export` 那一行的注释，
#   这一步 = 你人工授权 recurring spend（红线：花钱前人审）。
# 本脚本不占端口、不杀进程；纯 compute + 写本地文件 + 退出。
# 告警落 monitoring/alerts/ 与 monitoring/ALERTS.md；Notion 镜像在会话内人工/MCP 完成。
set -uo pipefail   # 故意不用 -e：run.py 有告警时退出码 1/2 是信号，非失败

REPO="/Users/Zhuanz/Desktop/LilyGEOMaster"
cd "$REPO" || { echo "找不到仓库 $REPO"; exit 3; }

# ── 花钱授权闸（默认关闭。准备好每周真查豆包再取消注释）──
# export GEO_MONITOR_ALLOW_SPEND=1

# venv（优先 .venv，回退 venv）
if [ -d "$REPO/.venv" ]; then
  # shellcheck disable=SC1091
  source "$REPO/.venv/bin/activate"
elif [ -d "$REPO/venv" ]; then
  # shellcheck disable=SC1091
  source "$REPO/venv/bin/activate"
fi

LOG_DIR="$REPO/monitoring/cron_logs"
mkdir -p "$LOG_DIR"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="$LOG_DIR/$TS.log"

{
  echo "=== Lily GEO 每周监测 @ $TS (UTC) ==="
  python -m geo.monitoring.run --segment A --refresh
  RC=$?
  echo "monitor exit=$RC  (0=无变化/基线  1=有告警  2=有P1告警)"
} >>"$LOG" 2>&1

echo "$TS 监测完成 → $LOG"
