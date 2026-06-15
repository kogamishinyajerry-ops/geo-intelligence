"""旅游 GEO 专属分析：基于【景点占答】信号（非联网引用 auth）。

为什么单独写（不复用 Lily selection.py）：
  Lily 的可赢度评分基于联网引用的 auth 分；旅游走普通接口=零引用，套用会让所有 query
  落入 n_citations==0 分支误判"观望"。旅游的真信号 = 豆包答案里**推荐了哪些景点**。

三张表（全部纯函数，每行带 capture_ids 可回溯）：
  1. attraction_leaderboard  景点占答排行 —— 谁占了 AI 心智里的"上海旅游"
  2. opportunity_map         机会图(per-query) —— 哪些问题答得泛/空位 = 内容机会
  3. content_shortlist       内容可赢度短名单 —— 该先产哪些主题的内容
"""
from __future__ import annotations

from collections import Counter

from geo.evidence.schema import BuyerSegment, Capture
from geo.evidence.store import EvidenceStore
from geo.config import get_settings
from geo.metrics.core import first_choice_rate, opportunity_score


def load_captures(segment: BuyerSegment | None = None) -> list[Capture]:
    caps = EvidenceStore(get_settings().evidence_dir).load_all()
    if segment is not None:
        caps = [c for c in caps if c.buyer_segment == segment]
    return caps


def attraction_leaderboard(captures: list[Capture]) -> list[dict]:
    """景点占答排行：每景点 in_answers（出现答案数）/ coverage（占总答比）/ first_choice（排第一次数）。
    按 coverage 降序、再 first_choice 降序。这是"谁是 AI 眼里的上海必去"的硬证据。"""
    n = len(captures)
    if n == 0:
        return []
    appears: Counter[str] = Counter()
    firsts: Counter[str] = Counter()
    for c in captures:
        for ent in set(c.named_brands):
            appears[ent] += 1
        if c.named_brands:
            firsts[c.named_brands[0]] += 1
    out = []
    for ent, cnt in appears.items():
        out.append({
            "attraction": ent,
            "in_answers": cnt,
            "coverage": round(cnt / n, 3),
            "first_choice": firsts.get(ent, 0),
            "first_choice_rate": round(firsts.get(ent, 0) / n, 3),
        })
    out.sort(key=lambda r: (r["coverage"], r["first_choice"]), reverse=True)
    return out


def _mega_set(captures: list[Capture], top: int = 8) -> set[str]:
    """跨全部 query 的头部景点（占答前 top）= 已被 AI 钉死的"巨头"，难撼动。"""
    return {r["attraction"] for r in attraction_leaderboard(captures)[:top]}


def opportunity_map(captures: list[Capture]) -> list[dict]:
    """机会图：每 query 一行。空位评分 + 命中景点数 + 首位景点 + 是否只返回巨头。"""
    from geo.category import active_profile

    qs = active_profile().queries
    _THEME = {q.text: q.theme for q in qs}
    _ORDER = {q.text: i for i, q in enumerate(qs)}

    by_q: dict[str, list[Capture]] = {}
    for c in captures:
        by_q.setdefault(c.query, []).append(c)
    mega = _mega_set(captures)

    rows = []
    for q, caps in by_q.items():
        ents = sorted({e for c in caps for e in c.named_brands})
        first = caps[0].named_brands[0] if caps[0].named_brands else None
        non_mega = [e for e in ents if e not in mega]
        rows.append({
            "query": q,
            "theme": _THEME.get(q, ""),
            "segment": caps[0].buyer_segment.value,
            "n_attractions": len(ents),
            "opportunity": round(opportunity_score(caps), 3),  # 1.0=无名单景点=纯空位
            "first": first,
            "attractions": ents,
            "non_mega": non_mega,  # 名单内但非巨头的景点（长尾，内容可带）
        })
    rows.sort(key=lambda r: _ORDER.get(r["query"], 999))
    return rows


def content_winnability(row: dict) -> dict:
    """内容可赢度（0-100）+ go/no-go + 理由。透明加权，旅游语义。

    高分 = AI 还没给出钉死的具体答案 → 一篇结构化真权威内容有机会定义/进入答案：
      - 纯空位（opportunity=1，无任何名单景点）：最高机会（但标注'或名单外景点'，诚实）
      - 命中景点少 / 多为长尾非巨头：中高（巨头未垄断，内容能带长尾进答案）
      - 只返回少数巨头（外滩/迪士尼…）：低（已被钉死，难撼动）
    """
    n = row["n_attractions"]
    gap = row["opportunity"]  # 0..1
    if gap >= 1.0:
        return {"score": 90.0, "go": "GO", "reason": "纯空位：豆包未点名任何名单景点 → 内容可定义答案（注意核实是否名单外景点）"}
    longtail = len(row["non_mega"])
    longtail_ratio = longtail / n if n else 0
    # 景点越少（AI 答得不饱满）+ 长尾占比越高（巨头没垄断）→ 越可赢
    thin = 1 - min(n / 12, 1.0)  # 命中越少越"薄"，越有内容空间
    score = round(100 * (0.45 * thin + 0.35 * longtail_ratio + 0.20 * (1 if longtail else 0)), 1)
    go = "GO" if score >= 55 else ("候选" if score >= 40 else "观望")
    reason = (
        f"命中{n}景点（{'薄·有空间' if n <= 6 else '饱满'}）；"
        f"长尾非巨头{longtail}个（{'巨头未垄断·可带长尾' if longtail else '多为巨头·难撼动'}）；"
        f"首位 {row['first'] or '—'}"
    )
    return {"score": score, "go": go, "reason": reason}


def content_shortlist(segment: BuyerSegment = BuyerSegment.A) -> list[dict]:
    rows = opportunity_map(load_captures(segment))
    out = [{**r, **content_winnability(r)} for r in rows]
    out.sort(key=lambda r: r["score"], reverse=True)
    return out


def console_report(segment: BuyerSegment = BuyerSegment.A) -> None:
    caps = load_captures(segment)
    print(f"=== 景点占答排行（segment {segment.value}, n={len(caps)} captures）===")
    print(f"{'景点':<14}{'答案数':<7}{'覆盖':<8}{'首选数':<7}{'首选率'}")
    for r in attraction_leaderboard(caps)[:25]:
        print(f"{r['attraction']:<14}{r['in_answers']:<7}{r['coverage']:<8}{r['first_choice']:<7}{r['first_choice_rate']}")
    print(f"\n=== 内容可赢度短名单（segment {segment.value}）===")
    for r in content_shortlist(segment):
        print(f"{r['score']:>5}  {r['go']:<5}[{r['theme']:<14}] {r['query']}")
        print(f"        {r['reason']}")


if __name__ == "__main__":
    import sys
    seg = BuyerSegment.A
    if "--c" in sys.argv:
        seg = BuyerSegment.C
    elif "--b" in sys.argv:
        seg = BuyerSegment.B
    console_report(seg)
