"""报表聚合：captures → 机会图(per-query) + 引用源排行(domain)。

纯读 / 纯函数式（除了 load 从磁盘）。不写 Notion——Notion 推送在编排层用聚合结果做。
每行都带 capture_ids，满足"可回溯证据 ID"红线。
"""
from __future__ import annotations

from statistics import mean

from geo.config import get_settings
from geo.evidence.schema import BuyerSegment, Capture
from geo.evidence.store import EvidenceStore
from geo.metrics.core import citation_leaderboard, opportunity_score


def load_captures(segment: BuyerSegment | None = None) -> list[Capture]:
    caps = EvidenceStore(get_settings().evidence_dir).load_all()
    if segment is not None:
        caps = [c for c in caps if c.buyer_segment == segment]
    return caps


def _avg_auth(caps: list[Capture]) -> float | None:
    xs = [s.auth_score for c in caps for s in c.cited_sources if s.auth_score is not None]
    return round(mean(xs), 3) if xs else None


def competition_level(top_coverage: float | None, avg_auth: float | None) -> str:
    """竞争强度启发式（GEO 视角）：头部源覆盖广 + 权威高 → 难抢；覆盖低/权威低 → 好切入。"""
    if not top_coverage:
        return "低"
    if top_coverage >= 0.5 and (avg_auth or 0) >= 0.6:
        return "高"
    if top_coverage >= 0.34:
        return "中"
    return "低"


def per_query_rows(captures: list[Capture]) -> list[dict]:
    """机会图：每 query 一行。带空位评分、头部引用源、竞争强度、证据 ID。"""
    from geo.category import active_profile

    prof = active_profile()
    qs = prof.queries
    _THEME = {q.text: q.theme for q in qs}
    _ORDER = {q.text: i for i, q in enumerate(qs)}
    _SHELF = prof.shelf

    by_q: dict[str, list[Capture]] = {}
    for c in captures:
        by_q.setdefault(c.query, []).append(c)

    rows = []
    for q, caps in by_q.items():
        lb = citation_leaderboard(caps)
        top = lb[0] if lb else None
        avg_auth = _avg_auth(caps)
        seg = caps[0].buyer_segment.value
        rows.append(
            {
                "query": q,
                "theme": _THEME.get(q, ""),
                "segment": seg,
                "shelf": _SHELF.get(seg, "未定"),
                "n_captures": len(caps),
                "n_citations": sum(len(c.cited_sources) for c in caps),
                "is_mock": any(c.is_mock for c in caps),
                "opportunity": round(opportunity_score(caps), 3),
                "named_brands": sorted({b for c in caps for b in c.named_brands}),
                "top_domain": top["domain"] if top else None,
                "top_site": top["site_name"] if top else None,
                "top_coverage": top["coverage"] if top else None,
                "avg_auth": avg_auth,
                "competition": competition_level(top["coverage"] if top else None, avg_auth),
                "capture_ids": [c.id for c in caps],
            }
        )
    rows.sort(key=lambda r: _ORDER.get(r["query"], 999))
    return rows


def console_report(captures: list[Capture]) -> None:
    print(f"=== 引用源排行（域名级占答率，n={len(captures)} captures）===")
    print(f"{'域名':<26}{'站点':<16}{'答案数':<7}{'覆盖':<7}{'被引':<6}{'auth':<6}")
    for r in citation_leaderboard(captures)[:15]:
        print(
            f"{(r['domain'] or '')[:25]:<26}{(r['site_name'] or '')[:15]:<16}"
            f"{r['in_answers']:<7}{r['coverage']:<7}{r['total_citations']:<6}{str(r['auth_avg']):<6}"
        )
    print("\n=== 机会图（per-query）===")
    for r in per_query_rows(captures):
        top = f"{r['top_site'] or r['top_domain'] or '—'}({r['top_coverage']})"
        print(
            f"[{r['theme']:<10}] 空位={r['opportunity']} 竞争={r['competition']} "
            f"头部={top} 引用={r['n_citations']}  {r['query']}"
        )


if __name__ == "__main__":
    import sys

    seg = BuyerSegment.A if "--b" not in sys.argv else BuyerSegment.B
    console_report(load_captures(seg))
