"""S2 · 响应结构断言哨兵——把「引用抽取静默归零」变「显式红灯」。

对存档真 raw_payload 跑结构断言，按 doubao._parse_references 的主路径重算「联网了几条/抽到几条」，
聚合「联网却零抽取」命中率对照历史基线骤降 → 产 EvolutionIntel(S2)。

红色风险消解（必须）：
  • use_search=False 品类（tourism）零引用是**设计基线**，绝不报漂移 → 直接返回 []。
  • 单轮/全批没联网（action_details 全空）≠ 引擎改了结构 → single_round_guard 不报。
  • 命中率全程从存档确定性重算，可回溯 capture_id；无基线只记录不报警。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from geo.category import active_profile
from geo.config import get_settings
from geo.evidence.store import EvidenceStore
from geo.evolution.intel import EvolutionIntel, make_intel_id

S2_DROP_DELTA = 0.30   # 联网抽取命中率较基线骤降阈值（顶置，便于人工校准）
S2_MIN_SEARCHED = 3    # 至少 N 条联网样本才判（滤小样本噪声）

_PARSER_VERSION = "doubao._parse_references/0.2.0"


def assert_reference_structure(raw: dict, n_extracted: int) -> dict:
    """对单条 raw_payload 跑结构断言（镜像 doubao._parse_references 主路径）。

    返回 {searched, n_results, n_extracted, structure_intact}。
      searched        : 本条是否触发联网（bot_usage.action_details 非空）
      n_results        : 主路径 results[] 计数
      n_extracted      : 实际抽到的引用数（= len(capture.cited_sources)，外部传入）
      structure_intact : searched 且 results 路径存在且 n_results>0
    """
    action_details = (raw.get("bot_usage") or {}).get("action_details") or []
    searched = bool(action_details)
    n_results = 0
    for action in action_details:
        for tool in action.get("tool_details") or []:
            output = tool.get("output") or {}
            results = (((output.get("data") or {}).get("data") or {}).get("results")) or []
            n_results += len(results)
    return {
        "searched": searched,
        "n_results": n_results,
        "n_extracted": n_extracted,
        "structure_intact": searched and n_results > 0,
    }


def _load_raw(root: Path, raw_capture_path: str | None) -> dict | None:
    if not raw_capture_path:
        return None
    path = Path(root) / raw_capture_path
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None  # 单条坏 raw 不拖垮整批（命中率分母不含 skipped）


def run_s2(captures=None, *, baseline_rate: float | None = None,
           single_round_guard: bool = True, repo_root=None, now: str | None = None) -> list[EvolutionIntel]:
    """S2 哨兵主入口。proposal-only：只产 EvolutionIntel，绝不落地。"""
    prof = active_profile()
    if not prof.use_search:
        return []  # 不适用：该品类不联网，零引用是设计基线（绝不报漂移）

    settings = get_settings()
    root = Path(repo_root) if repo_root is not None else settings.category_root
    if captures is None:
        store = EvidenceStore(settings.evidence_dir)
        captures = [
            c for c in store.load_all()
            if (not c.is_mock) and c.buyer_segment.value in prof.real_segments
        ]

    searched_structs = []  # (capture, struct) for searched==True 的子集
    for c in captures:
        raw = _load_raw(root, c.raw_capture_path)
        if raw is None:
            continue
        struct = assert_reference_structure(raw, len(c.cited_sources))
        if struct["searched"]:
            searched_structs.append((c, struct))

    n_searched = len(searched_structs)
    if single_round_guard and n_searched == 0:
        return []  # 本批全没联网 → 不报机制漂移（区分「没联网」vs「结构变了」）
    if n_searched < S2_MIN_SEARCHED:
        return []  # 样本不足，不报

    zero_extract = [(c, s) for c, s in searched_structs if s["n_extracted"] == 0]
    hit_rate = round((n_searched - len(zero_extract)) / n_searched, 3)

    if baseline_rate is None:
        return []  # 无历史基线 → 只能记录不报警（基线落盘留待 P1/监测层统一）
    if (baseline_rate - hit_rate) < S2_DROP_DELTA:
        return []  # 未骤降

    stamp = now or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    cids = sorted(c.id for c, _ in zero_extract) or sorted(c.id for c, _ in searched_structs)
    seed = f"S2|{prof.pkg}|{baseline_rate}|{hit_rate}|{'|'.join(cids)}"
    intel = EvolutionIntel(
        intel_id=make_intel_id("S2", prof.pkg, seed),
        captured_at=stamp,
        signal_layer="S2",
        claim=(f"联网引用抽取命中率自基线 {baseline_rate} 降至 {hit_rate}"
               f"（{n_searched} 条联网样本中 {len(zero_extract)} 条抽到 0 引用）→ 引擎响应结构漂移嫌疑"),
        battlefield_type="qa_engine",
        evidence={
            "internal": [
                {"capture_id": c.id, "note": f"searched 但 n_results={s['n_results']} n_extracted=0"}
                for c, s in zero_extract
            ],
            "external": [],
            "machine_verifiable": {
                "baseline_rate": baseline_rate,
                "hit_rate": hit_rate,
                "n_searched": n_searched,
                "n_zero_extract": len(zero_extract),
                "parser_version": _PARSER_VERSION,
            },
        },
        confidence="single-source",          # 单数据源=本仓存档证据
        source_independence="first-party-archive",
        affected_assumption="geo.adapters.doubao._parse_references",
        proposed_change={
            "target_seam": "geo/adapters/doubao.py:_parse_references",
            "kind": "parser-path-review",
            "intent_sketch": "核对 bot_usage.action_details[].tool_details[].output.data.data.results[] "
                             "主路径是否被引擎改名/改层级；仅供人审，绝不直接喂 codegen 当 ground truth。",
            "blast_radius": "citation_leaderboard 及其全部下游派生指标（覆盖/权威/可赢度）",
            "reversibility": "high",
            "rederive_needed": True,
            "requires_codex_review": True,    # 安全边界（解析路径）→ 命中即审
        },
        first_seen=stamp,
    )
    return [intel]
