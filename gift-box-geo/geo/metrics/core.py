"""Core GEO metrics — PURE functions over a list[Capture] (红线 #1/#2).

每个函数对应 brief 的一个指标名，且只读 named_brands（证据派生字段）：
  mention_rate      提及率      —— 含该品牌的回答占比
  share_of_answer   占答率(SoV) —— 该品牌提及数 / 全品牌提及总数
  first_choice_rate 首选推荐率  —— 该品牌作为首个被提及的回答占比
  opportunity_score 空位评分    —— 无任何观察名单品牌的回答占比（答得泛=高机会）

调用方负责先按 engine / segment / query / 时间窗过滤，再传入这里。
"""
from __future__ import annotations

from collections import Counter

from geo.evidence.schema import Capture


def mention_rate(captures: list[Capture], brand: str) -> float:
    """提及率：含该品牌的回答占比。"""
    if not captures:
        return 0.0
    n = sum(1 for c in captures if brand in c.named_brands)
    return n / len(captures)


def share_of_answer(captures: list[Capture]) -> dict[str, float]:
    """占答率（share of voice）：每品牌提及次数 / 所有品牌提及总次数。
    每条回答内同一品牌只计一次（用 set 去重）。返回 {brand: share}。"""
    counts: Counter[str] = Counter()
    for c in captures:
        for b in set(c.named_brands):
            counts[b] += 1
    total = sum(counts.values())
    if total == 0:
        return {}
    return {b: counts[b] / total for b in counts}


def first_choice_rate(captures: list[Capture], brand: str) -> float:
    """首选推荐率：该品牌作为首个被提及（named_brands[0]）的回答占比。"""
    if not captures:
        return 0.0
    n = sum(1 for c in captures if c.named_brands and c.named_brands[0] == brand)
    return n / len(captures)


def opportunity_score(captures: list[Capture]) -> float:
    """空位评分：无任何观察名单品牌占据答案的回答占比。
    高分 = AI 答得泛 / 无品牌主导 = 高机会空位（brief §4.1）。"""
    if not captures:
        return 0.0
    n = sum(1 for c in captures if not c.named_brands)
    return n / len(captures)


def _avg(xs: list[float]) -> float | None:
    return round(sum(xs) / len(xs), 3) if xs else None


def citation_leaderboard(captures: list[Capture]) -> list[dict]:
    """域名级"占答率"排行（GEO 货架情报）——谁占了 AI 答案的引用位。

    每项：domain · site_name · in_answers(出现的 capture 数) · coverage(占总 capture 比)
         · total_citations(总被引次数) · auth/rel/freshness 均值。
    按 in_answers 降序、再 total_citations 降序。纯函数。
    """
    n = len(captures)
    by_dom: dict[str, dict] = {}
    for c in captures:
        seen: set[str] = set()
        for s in c.cited_sources:
            d = s.domain
            if not d:
                continue
            rec = by_dom.setdefault(
                d,
                {"domain": d, "site_name": s.site_name, "in_answers": 0,
                 "total_citations": 0, "_auth": [], "_rel": [], "_fresh": []},
            )
            rec["total_citations"] += 1
            if d not in seen:
                rec["in_answers"] += 1
                seen.add(d)
            if not rec["site_name"] and s.site_name:
                rec["site_name"] = s.site_name
            if s.auth_score is not None:
                rec["_auth"].append(s.auth_score)
            if s.rel_score is not None:
                rec["_rel"].append(s.rel_score)
            if s.freshness_score is not None:
                rec["_fresh"].append(s.freshness_score)

    out = []
    for rec in by_dom.values():
        out.append(
            {
                "domain": rec["domain"],
                "site_name": rec["site_name"],
                "in_answers": rec["in_answers"],
                "coverage": round(rec["in_answers"] / n, 3) if n else 0.0,
                "total_citations": rec["total_citations"],
                "auth_avg": _avg(rec["_auth"]),
                "rel_avg": _avg(rec["_rel"]),
                "freshness_avg": _avg(rec["_fresh"]),
            }
        )
    out.sort(key=lambda r: (r["in_answers"], r["total_citations"]), reverse=True)
    return out
