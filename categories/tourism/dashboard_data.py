"""旅游 GEO 仪表盘数据装配层 —— build_payload(segment) -> dict（喂给 dashboard_render.render_html）。

接缝定位：本模块是 assembler，**生产** PROJECT_BRIEF 数据契约的 payload；render 消费它。
红线（#1 证据优先 / #2 可复现）落地方式：
  - 所有数字只来自引擎纯函数（geo.metrics.core / geo.reporting.tourism）对存档 capture 的计算，禁旁路、禁写死。
  - 每条 opportunity / content_pipeline 行携带 capture_ids，可回溯到 evidence/captures/<id>.json。
  - real/mock 照实标注；联网引用源（cited_sources）旅游走普通接口=零引用 → 多为空数组，诚实呈现，绝不伪造。

实体 = 景点（非品牌）：leaderboard.kind="attraction"，entity_label="景点"。

⚠️ 关键差异（相对礼盒）：tourism.opportunity_map() / content_shortlist() 的行**不含 capture_ids**
   → 本模块按 query 把同 query 的 capture 分组，自行补 capture_ids = [c.id for c in caps_of_that_query]，
   保证可回溯红线（机会图每行能点回原文）。
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from geo.config import get_settings
from geo.evidence.schema import BuyerSegment, Capture
from geo.metrics.core import first_choice_rate, opportunity_score, share_of_answer
from geo.reporting.tourism import (
    attraction_leaderboard,
    content_shortlist,
    load_captures,
)

ENGINE_LABEL = "豆包（火山方舟）"

# 客群语义（旅游 GEO，已重定义）—— 用于 meta.segments 标注现状，不写死任何指标。
_SEGMENT_LABEL = {
    "A": "A 外地客（主战场·豆包普通接口）",
    "C": "C 本地客（豆包普通接口）",
    "B": "B 入境客（英文 AI · 待 key）",
}

# 内容草稿对应的客群（用于流水线展示；草稿主题决定客群，非引擎指标）。
_DRAFT_SEGMENT_HINT = {
    "offbeat": "C",
    "family": "A",
    "kids": "A",
    "citywalk": "A",
    "local": "C",
    "weekend": "C",
}


def _norm_segment(segment: str | BuyerSegment) -> BuyerSegment:
    if isinstance(segment, BuyerSegment):
        return segment
    return BuyerSegment(str(segment).strip().upper())


def _excerpt(text: str, limit: int = 1200) -> str:
    text = text or ""
    return text if len(text) <= limit else text[:limit].rstrip() + " …"


def _captures_by_query(caps: list[Capture]) -> dict[str, list[Capture]]:
    by_q: dict[str, list[Capture]] = {}
    for c in caps:
        by_q.setdefault(c.query, []).append(c)
    return by_q


def _build_meta(seg: BuyerSegment, caps: list[Capture]) -> dict:
    n = len(caps)
    n_mock = sum(1 for c in caps if c.is_mock)
    n_real = n - n_mock
    n_queries = len({c.query for c in caps})
    models = sorted({c.engine_model for c in caps if c.engine_model})
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "category": "tourism",
        "title": "上海文旅 · AI 可见度遥测",
        "subtitle": "豆包答「上海去哪玩」时推荐了谁 · 哪里是景点空位 · 产真权威内容占位",
        "entity_label": "景点",
        "engine": ENGINE_LABEL,
        "engine_models": models,
        "generated_at": generated_at,
        "n_captures": n,
        "n_real": n_real,
        "n_mock": n_mock,
        "n_queries": n_queries,
        "segments": [_SEGMENT_LABEL.get(seg.value, seg.value)],
        "evidence_dir": "evidence/captures",
        "honesty": _build_honesty(),
    }


def _build_honesty() -> dict:
    return {
        "real_engines": ["豆包（火山方舟，普通接口，中文侧）"],
        "pending_engines": ["Perplexity / OpenAI（入境英文客 B，待 key）"],
        "caveats": [
            "联网 /bots 接口有日配额墙(429)→引用源情报暂缺，待配额恢复另跑一轮补",
            "门票/开放时间/预约/交通会变，景点信息发布前核实，不编造",
            "普通接口=零联网引用 → 多数回答无 cited_sources / 无 auth 分，这是真实情况，照实呈现",
            "C 本地客已少量真侦察 / B 入境英文客待 key，本盘默认 A 外地客主战场",
        ],
    }


def _build_kpis(caps: list[Capture], leaderboard: list[dict]) -> list[dict]:
    """4-6 个遥测读数 —— 全部由真证据纯函数派生，trace 指向计算来源。"""
    n = len(caps)
    n_mock = sum(1 for c in caps if c.is_mock)
    real_txt = "全 REAL 真侦察 · 可逐条回溯" if n_mock == 0 else f"{n - n_mock} real · {n_mock} mock · 可逐条回溯"
    top = leaderboard[0] if leaderboard else None
    # 空位率：无任何上榜景点占据的回答占比（与 opportunity_score 同义，逐 capture）。
    n_void = sum(1 for c in caps if not c.named_brands)
    void_rate = n_void / n if n else 0.0
    n_attractions = len({a for c in caps for a in c.named_brands})
    kpis = [
        {
            "label": "景点空位率",
            "value": round(void_rate, 4),
            "unit": "",
            "sub": f"{n_void}/{n} 条回答未点名任何上榜景点 = 可被内容定义的空位",
            "trace": "opportunity_score",
        },
        {
            "label": "证据样本",
            "value": n,
            "unit": "条",
            "sub": f"{len({c.query for c in caps})} query · {real_txt}",
            "trace": "evidence/captures",
        },
        {
            "label": "上榜景点",
            "value": n_attractions,
            "unit": "个",
            "sub": "白名单确定性抽取（非 LLM）命中的不同景点数",
            "trace": "named_brands",
        },
    ]
    if top:
        kpis.append(
            {
                "label": "头部景点首选率",
                "value": round(top["first_choice_rate"], 4),
                "unit": "",
                "sub": f"{top['attraction']} 作为豆包首个推荐的回答占比",
                "trace": "first_choice_rate",
            }
        )
        kpis.append(
            {
                "label": "头部景点覆盖",
                "value": round(top["coverage"], 4),
                "unit": "",
                "sub": f"{top['attraction']} 出现在 {top['in_answers']}/{n} 条回答里",
                "trace": "attraction_leaderboard.coverage",
            }
        )
    return kpis


def _build_hero(caps: list[Capture], leaderboard: dict, opportunity: list[dict]) -> dict:
    """30 秒头号发现：旅游 = 头部景点钉死 + 机会在长尾。全部来自真值，不写死。"""
    rows = leaderboard["rows"]
    top = rows[0] if rows else None
    n_go = sum(1 for o in opportunity if o.get("go") == "GO")
    if top is not None:
        headline = f"{top['attraction']}钉死「上海必去」头部"
        emphasis = (
            f"占答 {round((top['coverage'] or 0) * 100, 1)}% · "
            f"首选 {round((top['first_choice_rate'] or 0) * 100, 1)}%"
        )
        detail = f"头部锁死，真机会在 {n_go} 条 GO 长尾（亲子 / 小众 / 本地客专线）"
        tone = "locked"
    else:
        gap = opportunity_score(caps)
        headline = f"{round(gap * 100)}% 的回答未点名任何上榜景点"
        emphasis = "可被内容定义的空位"
        detail = f"{n_go} 条 GO 机会待攻"
        tone = "opportunity"
    return {"tone": tone, "headline": headline, "emphasis": emphasis, "detail": detail}


def _build_leaderboard(caps: list[Capture]) -> dict:
    rows = attraction_leaderboard(caps)[:20]
    return {
        "kind": "attraction",
        "title": "景点占答排行 · 谁是 AI 眼里的「上海必去」",
        "subtitle": "覆盖=出现在多少比例回答里；首选率=被排在第一位的回答占比（点表头可排序）",
        "columns": [
            {"key": "attraction", "label": "景点", "fmt": "text"},
            {"key": "in_answers", "label": "答案数", "fmt": "num"},
            {"key": "coverage", "label": "覆盖", "fmt": "pct"},
            {"key": "first_choice", "label": "首选数", "fmt": "num"},
            {"key": "first_choice_rate", "label": "首选率", "fmt": "pct"},
        ],
        "rows": rows,
    }


def _build_sov(caps: list[Capture]) -> list[dict]:
    sov = share_of_answer(caps)
    ranked = sorted(sov.items(), key=lambda kv: kv[1], reverse=True)[:12]
    return [{"entity": ent, "share": share} for ent, share in ranked]


def _build_opportunity(seg: BuyerSegment, by_query: dict[str, list[Capture]]) -> list[dict]:
    """content_shortlist 行 → 契约 opportunity 行。

    旅游差异：
      - shortlist 行无 capture_ids → 按 query 从 by_query 补 [c.id for c in caps]（可回溯红线）。
      - 旅游零联网引用 → competition 字段无意义 → 省略（None）；n_citations 恒 0。
      - top.coverage = 该首位景点在本盘的真实覆盖（从 attraction_leaderboard 查），无则 None。
    """
    shortlist = content_shortlist(seg)
    # 首位景点 → 全盘覆盖（真值，不估算）
    all_caps = [c for caps in by_query.values() for c in caps]
    cov_by_attr = {r["attraction"]: r["coverage"] for r in attraction_leaderboard(all_caps)}

    out: list[dict] = []
    for r in shortlist:
        q = r["query"]
        caps = by_query.get(q, [])
        first = r.get("first")
        top = None
        if first:
            top = {"label": first, "coverage": cov_by_attr.get(first)}
        out.append(
            {
                "query": q,
                "theme": r.get("theme", ""),
                "segment": r.get("segment", seg.value),
                "opportunity": r["opportunity"],
                "competition": None,  # 旅游零引用 → 无引用竞争维度，诚实留空
                "score": r["score"],
                "go": r["go"],
                "reason": r["reason"],
                "entities": r.get("attractions", [])[:6],
                "top": top,
                "n_citations": 0,  # 普通接口零联网引用，照实
                "capture_ids": [c.id for c in caps],  # ⚠️ 自补，shortlist 行不含
            }
        )
    return out


def _build_evidence(opportunity: list[dict], by_id: dict[str, Capture]) -> dict:
    """对所有 opportunity 涉及的 capture 建 brief（同 gift-box 规则）。

    cited_sources 旅游多为空数组（普通接口零联网引用），照实，不伪造。
    """
    evidence: dict[str, dict] = {}
    wanted: set[str] = set()
    for o in opportunity:
        wanted.update(o.get("capture_ids", []))
    for cid in sorted(wanted):
        c = by_id.get(cid)
        if c is None:
            continue
        evidence[cid] = {
            "query": c.query,
            "segment": c.buyer_segment.value,
            "engine_model": c.engine_model or "",
            "timestamp": c.timestamp.isoformat(),
            "is_mock": c.is_mock,
            "raw_excerpt": _excerpt(c.raw_answer),
            "named_brands": list(c.named_brands),
            "cited_sources": [
                {
                    "domain": s.domain,
                    "site_name": s.site_name,
                    "title": s.title,
                    "auth_score": s.auth_score,
                    "rel_score": s.rel_score,
                    "freshness_score": s.freshness_score,
                }
                for s in c.cited_sources
            ],
        }
    return evidence


def _build_monitoring() -> dict:
    """读 monitoring/history/*.json → 时间序列点；tourism 现 0 个 → 优雅降级 + 诚实 note。"""
    hist_dir = get_settings().category_root / "monitoring" / "history"
    points: list[dict] = []
    if hist_dir.is_dir():
        import json

        for p in sorted(hist_dir.glob("*.json")):
            try:
                snap = json.loads(p.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                continue
            points.append(
                {
                    "captured_at": snap.get("captured_at") or snap.get("timestamp") or p.stem,
                    "top_label": snap.get("top_label") or snap.get("top") or "",
                    "top_coverage": snap.get("top_coverage"),
                    "n_captures": snap.get("n_captures"),
                }
            )
    available = len(points) >= 2
    if points:
        note = f"已采 {len(points)} 个快照；≥2 个对齐快照后升级为时间序列遥测带。"
    else:
        note = "监测刚启动，monitoring/history/ 尚无快照 → 趋势线待建（首轮采集后逐轮追加）。"
    return {"available": available, "points": points, "note": note}


def _draft_title(md_path: Path) -> str:
    """草稿标题 = 首个 '# ' 一级标题；缺失则回退文件名。"""
    try:
        for line in md_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
    except OSError:
        pass
    return md_path.stem


def _draft_segment(stem: str) -> str | None:
    low = stem.lower()
    for key, seg in _DRAFT_SEGMENT_HINT.items():
        if key in low:
            return seg
    return None


def _build_content_pipeline(opportunity: list[dict]) -> list[dict]:
    """列 content/drafts/*.md。

    basis：草稿对外发布前必人审（红线 #3/#5）→ status 钉死「待审」。
    若能按客群把草稿挂到机会 query 上，则带该机会的 score/go/capture_ids（可回溯）；
    挂不上则 basis 留空（诚实：不硬编造关联）。
    """
    drafts_dir = get_settings().category_root / "content" / "drafts"
    if not drafts_dir.is_dir():
        return []
    items: list[dict] = []
    for md in sorted(drafts_dir.glob("*.md")):
        seg_hint = _draft_segment(md.stem)
        basis: dict = {"score": None, "go": None, "capture_ids": []}
        if seg_hint:
            seg_opps = [o for o in opportunity if o.get("segment") == seg_hint and o.get("go") == "GO"]
            if seg_opps:
                best = max(seg_opps, key=lambda o: o.get("score") or 0)
                basis = {
                    "score": best.get("score"),
                    "go": best.get("go"),
                    "capture_ids": best.get("capture_ids", []),
                }
        items.append(
            {
                "file": f"content/drafts/{md.name}",
                "title": _draft_title(md),
                "status": "待审（draft，景点信息发布前核实）",
                "basis": basis,
            }
        )
    return items


def build_payload(segment: str = "A") -> dict:
    """装配旅游 GEO 仪表盘 payload（严格契约形状）。默认 segment="A"（78 caps 主战场）。

    纯读：从证据库 load → 引擎纯函数计算 → 组装契约 dict（JSON 可序列化）。
    同输入两次结论一致（可复现红线）：唯一非确定字段 = meta.generated_at（采集时刻）。
    """
    seg = _norm_segment(segment)
    caps = load_captures(seg)
    by_query = _captures_by_query(caps)
    by_id = {c.id: c for c in caps}

    leaderboard = _build_leaderboard(caps)
    opportunity = _build_opportunity(seg, by_query)

    return {
        "meta": _build_meta(seg, caps),
        "hero": _build_hero(caps, leaderboard, opportunity),
        "kpis": _build_kpis(caps, leaderboard["rows"]),
        "leaderboard": leaderboard,
        "sov": _build_sov(caps),
        "opportunity": opportunity,
        "evidence": _build_evidence(opportunity, by_id),
        "monitoring": _build_monitoring(),
        "content_pipeline": _build_content_pipeline(opportunity),
    }
