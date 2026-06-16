#!/usr/bin/env python3
"""统一跨品类 GEO 机会指挥台 —— 把两个引擎的机会聚合成一个智能决策看板。

接缝定位：本工具是 **gatherer + CLI**，跨品类聚合 `opportunity` 行（已由各 repo 的
dashboard_data.build_payload 用纯函数算好），整形成统一机会模型，交 opportunity_render 渲染。

为什么走子进程而非 import：两个 repo 是各自独立的 `geo` 包（同名、各自 venv）→ 同进程 import
会撞名。各 repo 用**自己的 venv** 子进程 dump JSON，本工具只做合并 + 渲染，零第三方依赖（纯 stdlib）。

红线落地：① 不编造——所有机会/评分来自各 repo 纯函数对真证据的计算，本工具只重排+派生 action，
不重算指标；② 可回溯——每条机会带 capture_ids，evidence 抽屉可点回原文；③ 诚实——跨品类评分语义
不同（礼盒=引用权威弱+品牌空位；旅游=景点稀薄+长尾未垄断），统一排序为方向性参考，横幅明示。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# 品类展示元数据（title / 评分语义诚实标注）——仅展示层，绝不下沉进 geo/category.py 引擎层。
# 引擎层（geo.category._PROFILES）是品类 key 与顺序的唯一 SSOT；本表只补展示字段。
_DISPLAY = {
    "gift-box": {
        "title": "高端商务伴手礼盒",
        "score_basis": "引用权威弱 + 品牌空位（selection.winnability）",
    },
    "tourism": {
        "title": "上海文旅景点",
        "score_basis": "景点稀薄 + 长尾未垄断（tourism.content_winnability）",
    },
}


def _categories() -> list[dict]:
    """品类清单从引擎层 _PROFILES 派生（key + 顺序的 SSOT），_DISPLAY 仅补展示字段。

    fail-closed 双向断言：注册了引擎品类却缺展示元数据、或反之，都拒绝（红线：空集≠PASS，
    宁可显式报错也不静默漏渲染一个品类 / 跑一个幽灵品类）。"""
    from geo.category import all_profiles  # 函数内 import：子进程模型下不锁死品类

    keys = [p.key for p in all_profiles()]
    missing = [k for k in keys if k not in _DISPLAY]
    if missing:
        raise RuntimeError(
            f"品类 {missing} 在 geo.category._PROFILES 注册但缺展示元数据 "
            f"opportunity_board._DISPLAY → 拒绝静默漏渲染"
        )
    extra = [k for k in _DISPLAY if k not in keys]
    if extra:
        raise RuntimeError(
            f"opportunity_board._DISPLAY 含未注册品类 {extra}"
            f"（不在 geo.category._PROFILES）→ 拒绝跑幽灵品类"
        )
    return [{"key": k, **_DISPLAY[k]} for k in keys]

# 共享 venv 子进程跑：active profile.build_payload → JSON（带哨兵前缀，避开 venv 杂音行）。
# 走子进程而非 import：active_profile 由 GEO_CATEGORY 在进程级选定，两品类各起一个进程互不串台。
_DUMP = (
    "import json;"
    "from geo.category import active_profile;"
    "from importlib import import_module;"
    "p=active_profile();"
    "m=import_module(f'categories.{p.pkg}.dashboard_data');"
    "print('@@JSON@@'+json.dumps(m.build_payload(),ensure_ascii=False))"
)


def _load(cat: dict) -> dict:
    venv_py = ROOT / ".venv" / "bin" / "python"
    if not venv_py.exists():
        raise RuntimeError(f"{cat['key']}: 缺 venv {venv_py}（先 python -m venv .venv && pip install -e .）")
    env = {**os.environ, "GEO_CATEGORY": cat["key"]}
    proc = subprocess.run(
        [str(venv_py), "-c", _DUMP],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{cat['key']} build_payload 失败:\n{proc.stderr[-800:]}")
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("@@JSON@@")]
    if not lines:
        raise RuntimeError(f"{cat['key']}: 未拿到 JSON 输出\n{proc.stdout[-400:]}")
    return json.loads(lines[-1][len("@@JSON@@"):])


def _dividend(o: dict) -> float:
    """空位红利 0..1（连续、跨品类共用、可解释）：
    纯空位（无任何上榜实体占据答案）= 1.0（满红利，答案空间全开）；
    否则 = 1 - 头部实体覆盖（incumbent 越不垄断、头部越开 → 红利越高）。"""
    if (o.get("opportunity") or 0.0) >= 1.0:
        return 1.0
    top = o.get("top")
    if top and top.get("coverage") is not None:
        return round(max(0.0, 1.0 - float(top["coverage"])), 3)
    return 1.0


def _action(go: str | None, entity_label: str, draft_title: str | None) -> dict:
    """从真实 go 判定派生的行动建议（确定性，非 LLM）。"""
    if go == "GO" and draft_title:
        return {"kind": "draft", "text": f"草稿《{draft_title}》→ 人审放行后发布"}
    if go == "GO":
        return {"kind": "produce", "text": f"产真权威内容占位（{entity_label}空位）"}
    if go == "候选":
        return {"kind": "consider", "text": "候选：可产内容，优先级中"}
    return {"kind": "hold", "text": "观望/避：内容杠杆低 → 转品牌词 / 货架直答"}


# ── 战略态势 5 轴（全部 0..1、确定性纯函数、可回溯 capture_id、跨品类语义一致）──
# 🔴红线#1：绝不放 top.coverage 派生的「长尾可攻度」——该字段跨品类语义不一（礼盒=单 query 引用域名
# 覆盖、恒≈1.0；旅游=全盘景点覆盖、外滩 0.513），同轴叠加会捏造「礼盒长尾可攻度=0」假结论。
# 证据体量（绝对计数）也不入轴（需主观归一化才成 0..1，会引入拍脑袋分母）。
_SIT_AXES = [
    ("go_density", "GO 密度", "判为 GO 的机会占比 = 攻击面广度"),
    ("void_dividend", "空位红利", "GO 机会平均答案空间开放度（1−头部覆盖）"),
    ("pure_void", "纯空位率", "整片货架空着（无任一上榜实体）的机会占比"),
    ("cited_lever", "联网杠杆", "豆包对该品类联网取引用的机会占比（内容通道是否打开）"),
    ("evidence_trust", "证据可信度", "真侦察证据占比 n_real / n_captures"),
]
_SIT_STRONG, _SIT_WEAK = 0.70, 0.30  # 阈值与象限 GO_THRESH(0.55)/DIV_MID(0.5) 同量纲体系

# 工作流管线（结构性元数据 + 成熟度三态）。status 反映系统现状（measured=本仓已产真可回溯产物 /
# partial=能跑但覆盖未满 / declared=仅规格占位），随开发推进更新；非每跑实测值。
_SIT_PIPELINE = [
    ("侦察 Recon", "measured", "豆包真打取证"),
    ("指标 Metrics", "measured", "纯函数算占答率/空位"),
    ("监测 Monitoring", "partial", "周期 diff 告警（按快照触发）"),
    ("单品类看板", "measured", "8 区块真接证据"),
    ("机会指挥台", "measured", "跨品类聚合 + 可赢度排序"),
    ("部署 Schema", "partial", "草稿→JSON-LD，待人审 + 自有站"),
    ("Scout 演化侦查", "measured", "proposal-only 提案，恒 PROPOSED"),
    ("红线机器门", "measured", "fail-closed 机器可拒不可批"),
]


def _situation(opps: list[dict], cats: list[dict], pending_engines: list[str]) -> dict:
    """战略态势：从已聚合机会/品类【确定性派生】，零重算指标、零人工打分（红线#1/虚报零容忍）。

    5 轴全部对证据表的纯函数、可回溯 capture_id；优劣势按阈值机器派生（≥strong=强 / ≤weak=弱）。
    """
    labels = {key: lab for key, lab, _ in _SIT_AXES}
    by_cat: dict[str, dict] = {}
    for c in cats:
        k = c["key"]
        co = [o for o in opps if o["category"] == k]
        n = len(co) or 1
        go = [o for o in co if o["go"] == "GO"]
        vals = {
            "go_density": round(len(go) / n, 3),
            "void_dividend": round(sum(o["dividend"] for o in go) / len(go), 3) if go else 0.0,
            "pure_void": round(sum(1 for o in co if (o.get("opportunity") or 0) >= 1.0) / n, 3),
            "cited_lever": round(sum(1 for o in co if (o.get("n_citations") or 0) > 0) / n, 3),
            "evidence_trust": round(c["n_real"] / c["n_captures"], 3) if c.get("n_captures") else 0.0,
        }
        drivers = sorted(_SIT_AXES, key=lambda a: -vals[a[0]])[:2]
        by_cat[k] = {
            "title": c["title"],
            "values": vals,
            "strengths": [labels[key] for key, _, _ in _SIT_AXES if vals[key] >= _SIT_STRONG],
            "weaknesses": [labels[key] for key, _, _ in _SIT_AXES if vals[key] <= _SIT_WEAK],
            "drivers": [{"label": a[1], "value": vals[a[0]]} for a in drivers],
            "primary_play": c["score_basis"],  # 已有真数据口径，非 LLM 文案
        }
    return {
        "axes": [{"key": k, "label": lab, "hint": h} for k, lab, h in _SIT_AXES],
        "thresholds": {"strong": _SIT_STRONG, "weak": _SIT_WEAK},
        "by_category": by_cat,
        "pipeline": [{"label": lab, "status": st, "note": note} for lab, st, note in _SIT_PIPELINE],
        "declared_gaps": [{"label": e, "kind": "engine"} for e in pending_engines],
        "note": ("5 轴均为对证据表的确定性纯函数（可回溯 capture_id）；优劣势按阈值机器派生、非人工打分。"
                 "跨品类口径不同 → 雷达形状为方向性对比，非同尺度精确比较。"),
    }


def build_unified() -> dict:
    cats: list[dict] = []
    opps: list[dict] = []
    evidence: dict[str, dict] = {}
    real_engines: list[str] = []
    pending_engines: list[str] = []
    caveats: list[str] = []
    categories = _categories()  # 从引擎层 _PROFILES 派生（单 SSOT），fail-closed 断言已在内部

    for cat in categories:
        payload = _load(cat)
        meta = payload["meta"]
        el = meta["entity_label"]
        cats.append({
            "key": cat["key"],
            "title": cat["title"],
            "entity_label": el,
            "n_captures": meta["n_captures"],
            "n_real": meta["n_real"],
            "n_mock": meta["n_mock"],
            "engine": meta["engine"],
            "score_basis": cat["score_basis"],
        })
        hon = meta.get("honesty", {})
        real_engines += hon.get("real_engines", [])
        pending_engines += hon.get("pending_engines", [])
        caveats += hon.get("caveats", [])

        # capture_id → 草稿标题（从内容流水线 basis 反查，给机会挂上"已有草稿"）。
        cid2draft: dict[str, str] = {}
        for c in payload.get("content_pipeline", []):
            for cid in c.get("basis", {}).get("capture_ids", []):
                cid2draft.setdefault(cid, c["title"])

        # 合并 evidence（content-hash id 全局唯一；极端碰撞则按品类命名空间，绝不静默覆盖异值）。
        for cid, ev in payload.get("evidence", {}).items():
            key = cid
            if key in evidence and evidence[key].get("raw_excerpt") != ev.get("raw_excerpt"):
                key = f"{cat['key']}:{cid}"
            evidence[key] = {**ev, "category": cat["key"]}

        for o in payload.get("opportunity", []):
            draft_title = next((cid2draft[c] for c in o.get("capture_ids", []) if c in cid2draft), None)
            opps.append({
                **o,
                "category": cat["key"],
                "category_title": cat["title"],
                "entity_label": el,
                "score_basis": cat["score_basis"],
                "dividend": _dividend(o),
                "action": _action(o.get("go"), el, draft_title),
                "draft": draft_title,
            })

    opps.sort(key=lambda x: (-(x.get("score") or 0), x["category"], x["query"]))

    go_opps = [o for o in opps if o["go"] == "GO"]
    n_go = len(go_opps)
    n_candidate = sum(1 for o in opps if o["go"] == "候选")
    n_hold = len(opps) - n_go - n_candidate
    void_dividend = round(sum(o["dividend"] for o in go_opps) / n_go, 3) if n_go else 0.0
    by_category_go = {r["key"]: sum(1 for o in go_opps if o["category"] == r["key"]) for r in categories}

    return {
        "meta": {
            "title": "GEO 机会指挥台",
            "subtitle": "跨品类 · 真证据 · 可赢度排序 · 每条可回溯",
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "categories": cats,
        },
        "summary": {
            "total": len(opps),
            "n_go": n_go,
            "n_candidate": n_candidate,
            "n_hold": n_hold,
            "void_dividend": void_dividend,
            "best": go_opps[0] if go_opps else (opps[0] if opps else None),
            "by_category_go": by_category_go,
        },
        "opportunities": opps,
        "evidence": evidence,
        "situation": _situation(opps, cats, list(dict.fromkeys(pending_engines))),
        "honesty": {
            "real_engines": list(dict.fromkeys(real_engines)),
            "pending_engines": list(dict.fromkeys(pending_engines)),
            "caveats": [
                "跨品类评分语义不同：礼盒=引用权威弱+品牌空位；旅游=景点稀薄+长尾未垄断 → 统一排序为方向性参考，非同尺度精确比较",
                *dict.fromkeys(caveats),
            ],
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="统一跨品类 GEO 机会指挥台")
    ap.add_argument("--out", default=str(ROOT / "opportunity-board.html"), help="输出 HTML 路径")
    ap.add_argument("--json", action="store_true", help="只打印统一 payload JSON（不渲染）")
    args = ap.parse_args()

    payload = build_unified()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    sys.path.insert(0, str(ROOT))
    from opportunity_render import render_html

    html = render_html(payload)
    out = Path(args.out)
    out.write_text(html, encoding="utf-8")
    s = payload["summary"]
    bc = s["by_category_go"]
    go_breakdown = " / ".join(f"{c['title']} {bc.get(c['key'], 0)}" for c in payload["meta"]["categories"])
    print(f"机会指挥台 → {out}  ({out.stat().st_size // 1024} KB)")
    print(f"  机会 {s['total']} · GO {s['n_go']}（{go_breakdown}）"
          f" · 候选 {s['n_candidate']} · 观望 {s['n_hold']} · 空位红利均值 {s['void_dividend']}")
    if s["best"]:
        b = s["best"]
        print(f"  最佳机会: {b['query'][:34]}（{b['category_title']} · 可赢度 {b['score']}）")


if __name__ == "__main__":
    main()
