"""S5 · watchlist 外候选实体发现——确定性子串频次，**绝不用 LLM 当 ground truth**。

抽取信号 = markdown 加粗 `**实体**`（AI 答案枚举命名实体的干净边界，实测噪声最低）。
守卫：min_len + 双向子串排除已知 watchlist 词条（杜绝「珠广播电视塔」碎片）+ 结构性标签停用词
      + ≥min_captures 复现。每个候选可回溯 ≥min_captures 条 capture 子串，恒标 PROPOSED。

DECLARED-NOT-COVERED（已知边界，诚实标注、不装作覆盖）：
  • 抽取仅命中**纯 CJK 基本区**加粗实体；含数字/拉丁/间隔号·/全角括号的混合命名实体
    （如「M50创意园」「上海中心『上海之巅』观光厅」）不被抽取——这是有意的精度优先，
    避免放宽字符类引入碎片噪声回归。
  • 双向子串守卫偏保守（候选含已知短别名也排除）→ 偏向**精度**而非召回（proposal 宁缺毋滥）。
  漏报由 HITL/未来更强抽取补，绝不为提recall牺牲「零碎片」这条已验证不变式。
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timezone

from geo.category import active_profile
from geo.config import get_settings
from geo.evidence.store import EvidenceStore
from geo.evolution.intel import EvolutionIntel, make_intel_id
from geo.parsing import extract

# 加粗实体：3–12 个 CJK 字（2 字多为通用词/噪声，宁缺毋滥）
_BOLD = re.compile(r"\*\*([一-鿿]{3,12})\*\*")

# 结构性 markdown 小标题（加粗但非实体）——精确匹配剔除（不影响 "滨江森林公园" 这类专名）
_STOPWORDS = {
    "注意事项", "推荐玩法", "开放时间", "门票价格", "交通指南", "游玩攻略", "周边美食",
    "基本信息", "实用信息", "游玩路线", "游览路线", "特色亮点", "美食推荐", "最佳时间",
    "门票信息", "交通信息", "住宿推荐", "游玩攻略", "特别提醒", "温馨提示",
}


def _known_terms(watchlist: dict) -> set[str]:
    """watchlist 全部 name+aliases（lower），作候选排除集。"""
    out: set[str] = set()
    for items in watchlist.values():
        for it in items or []:
            if isinstance(it, dict):
                for t in [it.get("name"), *(it.get("aliases") or [])]:
                    if t:
                        out.add(t.lower())
    return out


def _is_known_related(cand: str, known_lower: set[str]) -> bool:
    """双向子串守卫：候选是任一已知词的子串、或反之 → 视为已知（不产候选）。"""
    cl = cand.lower()
    return any(cl in k or k in cl for k in known_lower)


def extract_candidate_terms(text: str) -> set[str]:
    """从单条 raw_answer 抽 markdown 加粗候选（确定性，去重）。"""
    return {m for m in _BOLD.findall(text or "")}


def _excerpt(text: str, term: str, pad: int = 20) -> str:
    i = text.find(term)
    if i < 0:
        return ""
    return text[max(0, i - pad): i + len(term) + pad].replace("\n", " ").strip()


def discover_candidates(captures=None, *, min_captures: int = 3, now: str | None = None) -> list[EvolutionIntel]:
    """S5 主入口。proposal-only：只产 EvolutionIntel，绝不写 watchlist/落地。"""
    prof = active_profile()
    settings = get_settings()
    if captures is None:
        store = EvidenceStore(settings.evidence_dir)
        captures = [
            c for c in store.load_all()
            if (not c.is_mock) and c.buyer_segment.value in prof.real_segments
        ]
    known = _known_terms(extract.load_watchlist(settings.watchlist_path))

    cap_ids: dict[str, set[str]] = defaultdict(set)   # candidate -> {capture_id}
    excerpts: dict[str, str] = {}                     # candidate -> 首个上下文
    for c in captures:
        for cand in extract_candidate_terms(c.raw_answer):
            if cand in _STOPWORDS or _is_known_related(cand, known):
                continue
            cap_ids[cand].add(c.id)
            excerpts.setdefault(cand, _excerpt(c.raw_answer, cand))

    stamp = now or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    out: list[EvolutionIntel] = []
    for cand in sorted(cap_ids):
        ids = sorted(cap_ids[cand])
        if len(ids) < min_captures:
            continue
        out.append(EvolutionIntel(
            intel_id=make_intel_id("S5", prof.pkg, f"S5|{prof.pkg}|{cand}"),
            captured_at=stamp,
            signal_layer="S5",
            claim=f"watchlist 外候选实体「{cand}」在 {len(ids)} 条回答中复现，疑似应进观察名单",
            battlefield_type="qa_engine",
            evidence={
                "internal": [{"capture_id": cid, "note": "加粗实体复现"} for cid in ids],
                "external": [],
                "machine_verifiable": {
                    "candidate": cand,
                    "occurrences": len(ids),
                    "capture_ids": ids,
                    "sample_excerpt": excerpts.get(cand, ""),
                },
            },
            confidence="single-source",
            source_independence="first-party-archive",
            affected_assumption=f"categories.{prof.pkg}.config.watchlist",
            proposed_change={
                "target_seam": f"categories/{prof.pkg}/config/watchlist.yaml",
                "kind": "watchlist-curation",
                "intent_sketch": f"人审确认「{cand}」是真实体（核对样本子串）+ 逐条确认 aliases 后由确定性脚本写入并 rederive 回填。",
                "blast_radius": "named_brands 抽取覆盖面（rederive 可零成本回填历史）",
                "reversibility": "high",
                "rederive_needed": True,
                "requires_codex_review": False,   # 加 watchlist 词条非代码安全边界
            },
            first_seen=stamp,
        ))
    return out
