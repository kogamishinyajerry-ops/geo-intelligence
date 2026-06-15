"""周期监测：把 GEO 指标冻成带时间戳快照，再 diff 出变化与告警。

snapshot.py  当前证据 → 派生指标快照（monitoring/history/）
diff.py      两份快照 → 结构化变化 + 人读告警行（进 Notion 控制塔）
run.py       batch?→snapshot→diff(vs last)→告警 的编排（不在本包内自动发布）
"""
