"""仪表盘数据装配层 —— captures → 数据契约 payload（喂 dashboard_render.render_html）。

**唯一职责 = 装配**：复用已有引擎（aggregate / selection / metrics.core）算指标，把结果整形成
PROJECT_BRIEF 锁定的数据契约形状。**禁止旁路**：不在此重算任何指标，不写死任何指标数字——
每个数都来自纯函数 / 真实 captures，可回溯 capture_id（红线 #1/#2）。

接缝：assembler（本模块）生产 payload，render（dashboard_render）消费它。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from geo.config import get_settings
from geo.evidence.schema import BuyerSegment, Capture
from geo.evidence.store import EvidenceStore
from geo.metrics.core import (
    citation_leaderboard,
    opportunity_score,
    share_of_answer,
)
from geo.reporting.aggregate import load_captures
from geo.reporting.selection import shortlist

# ── 装配常量（品类元信息，非指标数字；指标一律来自纯函数）──
_ENGINE = "豆包（火山方舟）"
_CATEGORY = "gift-box"
_ENTITY_LABEL = "品牌"
_TITLE = "高端商务伴手礼盒 · AI 可见度遥测"
_SUBTITLE = "测量豆包回答里推荐了谁、哪里是品牌空位、产权威内容占位"

_HONESTY = {
    "real_engines": ["豆包（火山方舟，中文侧）"],
    "pending_engines": ["Perplexity / OpenAI（英文侧，待 key）"],
    "caveats": [
        "联网商品卡 C 端 API 不返回：国内商品卡信号需另走 C 端监测线。",
        "豆包联网触发非 100%：裸 query 高频命中，加“请联网搜索”反而抑制触发。",
        "当前仅 segment A（中文侧）有真实证据；segment B 英文侧待 key 后切真。",
    ],
}


def build_payload(segment: str | None = None) -> dict:
    """captures → 数据契约 payload（JSON 可序列化 dict）。

    segment=None → 全部（gift-box 现仅 segment A 有真数据）。所有指标来自纯函数 /
    真实 captures，可回溯 capture_id；除 meta.generated_at 外，同输入两次结果一致（可复现）。
    """
    seg_enum = BuyerSegment(segment) if segment is not None else None
    caps = load_captures(seg_enum)
    settings = get_settings()

    meta = _build_meta(caps, settings)
    leaderboard = _build_leaderboard(caps)
    sov = _build_sov(caps)
    opportunity = _build_opportunity(seg_enum)
    evidence = _build_evidence(opportunity, settings)
    monitoring = _build_monitoring()
    content_pipeline = _build_content_pipeline(opportunity)
    kpis = _build_kpis(caps, leaderboard, opportunity)
    hero = _build_hero(caps, leaderboard, opportunity)

    return {
        "meta": meta,
        "hero": hero,
        "kpis": kpis,
        "leaderboard": leaderboard,
        "sov": sov,
        "opportunity": opportunity,
        "evidence": evidence,
        "monitoring": monitoring,
        "content_pipeline": content_pipeline,
    }


# ── meta ──────────────────────────────────────────────────────────────────

def _build_meta(caps: list[Capture], settings) -> dict:
    n_mock = sum(1 for c in caps if c.is_mock)
    engine_models = sorted({c.engine_model for c in caps if c.engine_model})
    return {
        "category": _CATEGORY,
        "title": _TITLE,
        "subtitle": _SUBTITLE,
        "entity_label": _ENTITY_LABEL,
        "engine": _ENGINE,
        "engine_models": engine_models,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_captures": len(caps),
        "n_real": len(caps) - n_mock,
        "n_mock": n_mock,
        "n_queries": len({c.query for c in caps}),
        "segments": sorted({c.buyer_segment.value for c in caps}),
        "evidence_dir": str(settings.evidence_dir / "captures"),
        "honesty": _HONESTY,
    }


# ── leaderboard（kind=citation）─────────────────────────────────────────────

def _build_leaderboard(caps: list[Capture]) -> dict:
    rows_raw = citation_leaderboard(caps)[:15]
    rows = [
        {
            "domain": r["domain"],
            "site_name": r["site_name"],
            "in_answers": r["in_answers"],
            "coverage": r["coverage"],
            "total_citations": r["total_citations"],
            "auth_avg": r["auth_avg"],
            "rel_avg": r["rel_avg"],
            "freshness_avg": r["freshness_avg"],
        }
        for r in rows_raw
    ]
    return {
        "kind": "citation",
        "title": "引用源排行 · 谁占了 AI 答案的引用位",
        "subtitle": "域名级占答率（出现的回答数 / 总回答数），按占答降序",
        "columns": [
            {"key": "domain", "label": "域名 / 站点", "fmt": "text"},
            {"key": "in_answers", "label": "出现答数", "fmt": "num"},
            {"key": "coverage", "label": "覆盖", "fmt": "pct"},
            {"key": "total_citations", "label": "被引次数", "fmt": "num"},
            {"key": "auth_avg", "label": "权威均值", "fmt": "score"},
        ],
        "rows": rows,
    }


# ── sov（share_of_answer 降序 [:10]）────────────────────────────────────────

def _build_sov(caps: list[Capture]) -> list[dict]:
    shares = share_of_answer(caps)
    ordered = sorted(shares.items(), key=lambda kv: kv[1], reverse=True)[:10]
    return [{"entity": entity, "share": share} for entity, share in ordered]


# ── opportunity（shortlist → 契约字段）─────────────────────────────────────

def _build_opportunity(seg_enum: BuyerSegment | None) -> list[dict]:
    """shortlist() 短名单 → 机会图行。shortlist 内部锁 segment A（真数据侧），
    若调用方限定到 A（或全部）则采纳；限定到非 A segment 则空（诚实，无真数据不编）。"""
    if seg_enum is not None and seg_enum is not BuyerSegment.A:
        return []
    rows = shortlist()
    out = []
    for r in rows:
        top_label = r["top_site"] or r["top_domain"]
        top = {"label": top_label, "coverage": r["top_coverage"]} if top_label else None
        out.append(
            {
                "query": r["query"],
                "theme": r["theme"],
                "segment": r["segment"],
                "opportunity": r["opportunity"],
                "competition": r["competition"],
                "score": r["score"],
                "go": r["go"],
                "reason": r["reason"],
                "entities": list(r["named_brands"]),
                "top": top,
                "n_citations": r["n_citations"],
                "capture_ids": list(r["capture_ids"]),
            }
        )
    return out


# ── evidence（opportunity.capture_ids 里所有 capture → brief）────────────────

def _build_evidence(opportunity: list[dict], settings) -> dict:
    """对所有出现在 opportunity.capture_ids 里的 capture 建 {id: brief}，可回溯。"""
    wanted: set[str] = set()
    for o in opportunity:
        wanted.update(o.get("capture_ids", []))
    if not wanted:
        return {}

    store = EvidenceStore(settings.evidence_dir)
    evidence: dict[str, dict] = {}
    for cid in sorted(wanted):
        cap = store.load(cid)
        evidence[cid] = {
            "query": cap.query,
            "segment": cap.buyer_segment.value,
            "engine_model": cap.engine_model,
            "timestamp": cap.timestamp.isoformat(),
            "is_mock": cap.is_mock,
            "raw_excerpt": cap.raw_answer[:280],
            "named_brands": list(cap.named_brands[:10]),
            "cited_sources": [
                {
                    "domain": s.domain,
                    "site_name": s.site_name,
                    "title": s.title,
                    "auth_score": s.auth_score,
                    "rel_score": s.rel_score,
                    "freshness_score": s.freshness_score,
                }
                for s in cap.cited_sources[:5]
            ],
        }
    return evidence


# ── monitoring（读 monitoring/history/*.json）───────────────────────────────

def _build_monitoring() -> dict:
    history_dir = get_settings().category_root / "monitoring" / "history"
    files = sorted(history_dir.glob("*.json")) if history_dir.exists() else []
    if not files:
        return {
            "available": False,
            "points": [],
            "note": "监测线尚未落历史快照；首轮 snapshot --save 后此处升级为趋势遥测带。",
        }

    points = []
    for f in files:
        snap = json.loads(f.read_text(encoding="utf-8"))
        lb = snap.get("citation_leaderboard") or []
        top = lb[0] if lb else None
        points.append(
            {
                "captured_at": snap.get("captured_at", ""),
                "top_label": (top.get("site_name") or top.get("domain")) if top else "—",
                "top_coverage": top.get("coverage") if top else None,
                "n_captures": snap.get("n_captures", 0),
            }
        )
    points.sort(key=lambda p: p["captured_at"])
    note = (
        f"已采 {len(points)} 个历史快照，绘制头部源占答覆盖随时间的趋势。"
        if len(points) >= 2
        else "仅 1 个历史快照，趋势需 ≥2 个对齐快照；后续每轮监测自动追加。"
    )
    return {"available": True, "points": points, "note": note}


# ── content_pipeline（content/drafts/*.md → 条目）───────────────────────────

def _draft_title(path: Path) -> str:
    """文件首个 '# ' 标题行；无则用文件名。"""
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
    return path.name


def _draft_target_query(path: Path) -> str | None:
    """草稿里的 '目标 query：' 行（用于和 shortlist query 匹配上稿依据）。"""
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip().lstrip(">").strip()
        if s.startswith("目标 query"):
            # 形如 "目标 query：xxx" — 取冒号后内容
            for sep in ("：", ":"):
                if sep in s:
                    return s.split(sep, 1)[1].strip()
    return None


def _build_content_pipeline(opportunity: list[dict]) -> list[dict]:
    """列 content/drafts/*.md，basis 尽量从机会图按 query 匹配（匹配不到给空 capture_ids，不编造）。"""
    category_root = get_settings().category_root
    drafts_dir = category_root / "content" / "drafts"
    if not drafts_dir.exists():
        return []

    by_query = {o["query"]: o for o in opportunity}

    def match_opp(target_q: str | None) -> dict | None:
        if not target_q:
            return None
        if target_q in by_query:
            return by_query[target_q]
        # 软匹配：草稿目标 query 与机会图 query 互为子串（草稿常合并多个 query）
        for q, o in by_query.items():
            if q and (q in target_q or target_q in q):
                return o
        return None

    out = []
    for path in sorted(drafts_dir.glob("*.md")):
        target_q = _draft_target_query(path)
        opp = match_opp(target_q)
        if opp is not None:
            basis = {
                "score": opp["score"],
                "go": opp["go"],
                "capture_ids": list(opp["capture_ids"]),
            }
        else:
            basis = {"score": None, "go": None, "capture_ids": []}
        out.append(
            {
                "file": str(path.relative_to(category_root)),
                "title": _draft_title(path),
                "status": "待审（draft，发布前人审）",
                "basis": basis,
            }
        )
    return out


# ── kpis（4-6 个遥测读数，全部来自真实 captures / 纯函数）──────────────────

def _build_kpis(caps: list[Capture], leaderboard: dict, opportunity: list[dict]) -> list[dict]:
    n = len(caps)
    n_mock = sum(1 for c in caps if c.is_mock)
    real_txt = "全部 real（豆包联网）" if n_mock == 0 else f"{n - n_mock} real · {n_mock} mock"
    gap = opportunity_score(caps)  # 空位率：无任何名单品牌占据的回答占比
    lb_rows = leaderboard["rows"]
    top = lb_rows[0] if lb_rows else None
    n_go = sum(1 for o in opportunity if o.get("go") == "GO")
    total_citations = sum(len(c.cited_sources) for c in caps)

    kpis: list[dict] = [
        {
            "label": "品牌空位率",
            "value": gap,
            "unit": "",
            "sub": f"{sum(1 for c in caps if not c.named_brands)}/{n} 条回答无上榜品牌占据",
            "trace": f"opportunity_score · n={n}",
        },
        {
            "label": "真实证据",
            "value": n,
            "unit": "条",
            "sub": f"{len({c.query for c in caps})} query · {real_txt}",
            "trace": "evidence/captures/",
        },
    ]
    if top is not None:
        kpis.append(
            {
                "label": "头号 incumbent",
                "value": top["site_name"] or top["domain"],
                "unit": "",
                "sub": f"占答 {round((top['coverage'] or 0) * 100, 1)}% · 权威 {top['auth_avg']}（软文为主，好打）",
                "trace": f"citation_leaderboard[0] · {top['domain']}",
            }
        )
    kpis.append(
        {
            "label": "GO 机会",
            "value": n_go,
            "unit": "条",
            "sub": f"可赢度 ≥55 的攻击 query（共 {len(opportunity)} 条机会评分）",
            "trace": "selection.shortlist",
        }
    )
    kpis.append(
        {
            "label": "总引用源",
            "value": total_citations,
            "unit": "条",
            "sub": "豆包答案里被引的外部链接总数（含权威分）",
            "trace": "sum(cited_sources)",
        }
    )
    return kpis


# ── hero（头号发现，从真值派生，category-aware）─────────────────────────────

def _build_hero(caps: list[Capture], leaderboard: dict, opportunity: list[dict]) -> dict:
    """30 秒头号发现：礼盒 = 高空位 + 软文 incumbent 可取代。全部来自真值，不写死。"""
    gap = opportunity_score(caps)
    rows = leaderboard["rows"]
    top = rows[0] if rows else None
    n_go = sum(1 for o in opportunity if o.get("go") == "GO")
    headline = f"{round(gap * 100)}% 的豆包答案没有任何上榜品牌名"
    emphasis = "整片货架空着"
    if top is not None:
        auth = top.get("auth_avg")
        soft = "软文为主·好打" if (auth is not None and auth <= 0.5) else "权威中等"
        detail = (
            f"头号 incumbent {top['site_name'] or top['domain']} 占引用 "
            f"{round((top['coverage'] or 0) * 100, 1)}%（auth {auth}，{soft}）→ 可被真权威内容取代；"
            f"{n_go} 条 GO 机会待攻"
        )
    else:
        detail = f"{n_go} 条 GO 机会待攻"
    return {"tone": "opportunity", "headline": headline, "emphasis": emphasis, "detail": detail}


if __name__ == "__main__":
    import sys

    seg = sys.argv[1] if len(sys.argv) > 1 else None
    payload = build_payload(seg)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
