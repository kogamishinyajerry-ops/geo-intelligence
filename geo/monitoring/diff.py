"""周期监测 · 对比：两份快照 → 结构化变化 + 人读告警行。

纯函数。所有判断只基于快照里的派生指标，不重新查 API。
告警按优先级排序，可直接进 Notion 控制塔：
  P1 品牌空位被占 —— 此前无品牌的 query，豆包开始点名品牌 → 机会窗口收窄，最该响应
  P2 新对手 / 新品牌 / 联网消失 —— 竞争格局变化
  P3 覆盖/权威/新鲜度/空位 移动 —— 趋势观察

阈值集中在顶部，便于人工校准（首版为保守经验值，非官方数字）。
"""
from __future__ import annotations

# ── 显著变化阈值 ──
COVERAGE_DELTA = 0.10     # 域名占答率（覆盖）变化 ≥10pp 才报（12 captures 下约 1 个答案）
AUTH_DELTA = 0.05         # 引用权威均值移动
OPPORTUNITY_DELTA = 0.10  # 空位评分移动
SOV_DELTA = 0.05          # 品牌 share-of-voice 移动
FRESHNESS_DROP = 0.10     # 引用新鲜度下降（incumbent 内容变旧 = 机会开口）
NEW_DOMAIN_MIN_ANSWERS = 2  # 新对手至少站稳 2 个答案才报（滤掉单次偶现）

_LEVEL_ORDER = {"P1": 0, "P2": 1, "P3": 2}


def _by_domain(snap: dict) -> dict[str, dict]:
    return {r["domain"]: r for r in snap.get("citation_leaderboard", []) if r.get("domain")}


def _by_query(snap: dict) -> dict[str, dict]:
    return {r["query"]: r for r in snap.get("per_query", [])}


def diff_snapshots(old: dict, new: dict) -> dict:
    """old/new 两份快照 → 变化 dict（含 alerts）。old 为 None 时按"首测"处理（无变化）。"""
    if old is None:
        return {
            "from": None,
            "to": new.get("captured_at"),
            "segment": new.get("segment"),
            "baseline": True,
            "citation_changes": {"new_domains": [], "dropped_domains": [], "coverage_moves": [], "auth_moves": []},
            "freshness_flags": [],
            "brand_changes": {"new_brands": [], "dropped_brands": [], "sov_moves": []},
            "query_changes": [],
            "alerts": [],
        }

    old_lb, new_lb = _by_domain(old), _by_domain(new)
    old_q, new_q = _by_query(old), _by_query(new)

    # ── 引用层 ──
    new_domains = [new_lb[d] for d in new_lb if d not in old_lb]
    dropped_domains = [old_lb[d] for d in old_lb if d not in new_lb]
    coverage_moves, auth_moves, freshness_flags = [], [], []
    for d in old_lb.keys() & new_lb.keys():
        o, n = old_lb[d], new_lb[d]
        dc = round(n["coverage"] - o["coverage"], 3)
        if abs(dc) >= COVERAGE_DELTA:
            coverage_moves.append(
                {"domain": d, "site_name": n.get("site_name"), "from": o["coverage"], "to": n["coverage"], "delta": dc}
            )
        oa, na = o.get("auth_avg"), n.get("auth_avg")
        if oa is not None and na is not None and abs(na - oa) >= AUTH_DELTA:
            auth_moves.append({"domain": d, "site_name": n.get("site_name"), "from": oa, "to": na, "delta": round(na - oa, 3)})
        of, nf = o.get("freshness_avg"), n.get("freshness_avg")
        if of is not None and nf is not None and (of - nf) >= FRESHNESS_DROP:
            freshness_flags.append({"domain": d, "site_name": n.get("site_name"), "from": of, "to": nf, "delta": round(nf - of, 3)})

    # ── 品牌层 ──
    old_b, new_b = old.get("brand_sov", {}), new.get("brand_sov", {})
    new_brands = sorted(b for b in new_b if b not in old_b)
    dropped_brands = sorted(b for b in old_b if b not in new_b)
    sov_moves = []
    for b in old_b.keys() & new_b.keys():
        delta = round(new_b[b] - old_b[b], 3)
        if abs(delta) >= SOV_DELTA:
            sov_moves.append({"brand": b, "from": round(old_b[b], 3), "to": round(new_b[b], 3), "delta": delta})

    # ── query 层 ──
    query_changes = []
    for q in old_q.keys() & new_q.keys():
        o, n = old_q[q], new_q[q]
        do = round(n["opportunity"] - o["opportunity"], 3)
        gap_closed = (not o["named_brands"]) and bool(n["named_brands"])
        gap_opened = bool(o["named_brands"]) and (not n["named_brands"])
        cites_appeared = o["n_citations"] == 0 and n["n_citations"] > 0
        cites_vanished = o["n_citations"] > 0 and n["n_citations"] == 0
        if abs(do) >= OPPORTUNITY_DELTA or gap_closed or gap_opened or cites_appeared or cites_vanished:
            query_changes.append(
                {
                    "query": q,
                    "theme": n.get("theme"),
                    "opportunity_from": o["opportunity"],
                    "opportunity_to": n["opportunity"],
                    "opportunity_delta": do,
                    "brand_gap_closed": gap_closed,
                    "brand_gap_opened": gap_opened,
                    "citations_appeared": cites_appeared,
                    "citations_vanished": cites_vanished,
                    "old_brands": o["named_brands"],
                    "new_brands": n["named_brands"],
                }
            )

    alerts = build_alerts(
        new_domains, dropped_domains, coverage_moves, auth_moves, freshness_flags,
        new_brands, dropped_brands, sov_moves, query_changes,
    )
    return {
        "from": old.get("captured_at"),
        "to": new.get("captured_at"),
        "segment": new.get("segment"),
        "baseline": False,
        "citation_changes": {
            "new_domains": new_domains,
            "dropped_domains": dropped_domains,
            "coverage_moves": coverage_moves,
            "auth_moves": auth_moves,
        },
        "freshness_flags": freshness_flags,
        "brand_changes": {"new_brands": new_brands, "dropped_brands": dropped_brands, "sov_moves": sov_moves},
        "query_changes": query_changes,
        "alerts": alerts,
    }


def build_alerts(
    new_domains,
    dropped_domains=None,
    coverage_moves=None,
    auth_moves=None,
    freshness_flags=None,
    new_brands=None,
    dropped_brands=None,
    sov_moves=None,
    query_changes=None,
) -> list[dict]:
    """把变化翻译成带优先级的人读告警行。每行自带 level/kind/msg。

    新参数（dropped_domains/auth_moves/dropped_brands 等）默认 None→[] 归一：
    向后兼容 + fail-closed（空集零迭代不产告警，绝不兜底）。
    """
    dropped_domains = dropped_domains or []
    coverage_moves = coverage_moves or []
    auth_moves = auth_moves or []
    freshness_flags = freshness_flags or []
    new_brands = new_brands or []
    dropped_brands = dropped_brands or []
    sov_moves = sov_moves or []
    query_changes = query_changes or []
    alerts: list[dict] = []

    # P1：品牌空位被占（最高优先 —— 有人抢进了原本空白的 AI 答案）
    for qc in query_changes:
        if qc["brand_gap_closed"]:
            alerts.append(
                {
                    "level": "P1",
                    "kind": "品牌空位被占",
                    "msg": f"[{qc['theme']}]「{qc['query']}」豆包开始点名品牌：{'、'.join(qc['new_brands'])}"
                    f"（此前为品牌空位）→ 机会窗口收窄，优先抢内容/品牌词",
                }
            )

    # P2：联网消失（该 query 的 GEO 杠杆下降）
    for qc in query_changes:
        if qc["citations_vanished"]:
            alerts.append(
                {
                    "level": "P2",
                    "kind": "联网消失",
                    "msg": f"[{qc['theme']}]「{qc['query']}」豆包不再联网取证（引用归零）→ 内容 GEO 杠杆下降",
                }
            )
    # P2：新对手域名进入答案
    for d in new_domains:
        if d.get("in_answers", 0) >= NEW_DOMAIN_MIN_ANSWERS:
            alerts.append(
                {
                    "level": "P2",
                    "kind": "新对手",
                    "msg": f"新引用源进入豆包答案：{d.get('site_name') or d['domain']}（{d['domain']}）"
                    f"覆盖 {d['coverage']}、被引 {d['total_citations']}",
                }
            )
    # P2：对手域名退出答案（机会开口 —— 此前站稳的引用源消失，腾出位置）
    for d in dropped_domains:
        if d.get("in_answers", 0) >= NEW_DOMAIN_MIN_ANSWERS:
            alerts.append(
                {
                    "level": "P2",
                    "kind": "对手退出",
                    "msg": f"引用源退出豆包答案：{d.get('site_name') or d['domain']}（{d['domain']}）"
                    f"原覆盖 {d['coverage']}、原被引 {d['total_citations']} → 机会开口，可抢占其腾出的答案位",
                }
            )
    # P2：观察名单品牌从答案消失
    for b in dropped_brands:
        alerts.append(
            {"level": "P2", "kind": "品牌消失", "msg": f"豆包答案不再出现观察名单品牌：{b} → 该品牌 GEO 可见度归零"}
        )
    # P2：品牌层新出现品牌
    for b in new_brands:
        alerts.append({"level": "P2", "kind": "新品牌", "msg": f"豆包答案新出现观察名单品牌：{b}"})

    # P3：覆盖/权威/新鲜度/空位 趋势
    for m in coverage_moves:
        arrow = "↑" if m["delta"] > 0 else "↓"
        alerts.append(
            {
                "level": "P3",
                "kind": "覆盖移动",
                "msg": f"{m.get('site_name') or m['domain']} 占答率 {arrow} {m['from']}→{m['to']}（Δ{m['delta']:+}）",
            }
        )
    for m in auth_moves:
        arrow = "↑" if m["delta"] > 0 else "↓"
        hint = "该源更权威，挤压空间" if m["delta"] > 0 else "该源权威下降，机会开口"
        alerts.append(
            {
                "level": "P3",
                "kind": "权威移动",
                "msg": f"{m.get('site_name') or m['domain']} 引用权威均值 {arrow} {m['from']}→{m['to']}（Δ{m['delta']:+}）→ {hint}",
            }
        )
    for m in sov_moves:
        arrow = "↑" if m["delta"] > 0 else "↓"
        alerts.append(
            {"level": "P3", "kind": "品牌SoV移动", "msg": f"品牌 {m['brand']} SoV {arrow} {m['from']}→{m['to']}（Δ{m['delta']:+}）"}
        )
    for f in freshness_flags:
        alerts.append(
            {
                "level": "P3",
                "kind": "内容变旧",
                "msg": f"{f.get('site_name') or f['domain']} 引用新鲜度下降 {f['from']}→{f['to']} → 该源内容变旧，机会开口",
            }
        )
    for qc in query_changes:
        if abs(qc["opportunity_delta"]) >= OPPORTUNITY_DELTA:
            arrow = "↑" if qc["opportunity_delta"] > 0 else "↓"
            alerts.append(
                {
                    "level": "P3",
                    "kind": "空位移动",
                    "msg": f"[{qc['theme']}]「{qc['query']}」空位评分 {arrow} {qc['opportunity_from']}→{qc['opportunity_to']}",
                }
            )

    alerts.sort(key=lambda a: _LEVEL_ORDER.get(a["level"], 9))
    return alerts


def format_alerts(diff: dict) -> str:
    """把 diff 渲染成纯文本块（控制台/Notion 备注用）。"""
    if diff.get("baseline"):
        return f"📍 基线快照已建立（{diff['to']}），无对比对象。"
    alerts = diff.get("alerts", [])
    if not alerts:
        return f"✅ 无显著变化（{diff['from']} → {diff['to']}）。"
    lines = [f"⚠️ 监测告警（{diff['from']} → {diff['to']}），共 {len(alerts)} 条："]
    lines.extend(f"  {a['level']} · {a['kind']}：{a['msg']}" for a in alerts)
    return "\n".join(lines)
