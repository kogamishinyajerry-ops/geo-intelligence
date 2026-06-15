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

# 品类登记（key / 展示名 / 评分语义诚实标注）。合并后一个共享引擎，品类靠 GEO_CATEGORY 选。
CATEGORIES = [
    {
        "key": "gift-box",
        "title": "高端商务伴手礼盒",
        "score_basis": "引用权威弱 + 品牌空位（selection.winnability）",
    },
    {
        "key": "tourism",
        "title": "上海文旅景点",
        "score_basis": "景点稀薄 + 长尾未垄断（tourism.content_winnability）",
    },
]

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


def build_unified() -> dict:
    cats: list[dict] = []
    opps: list[dict] = []
    evidence: dict[str, dict] = {}
    real_engines: list[str] = []
    pending_engines: list[str] = []
    caveats: list[str] = []

    for cat in CATEGORIES:
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
    by_category_go = {r["key"]: sum(1 for o in go_opps if o["category"] == r["key"]) for r in CATEGORIES}

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
    print(f"机会指挥台 → {out}  ({out.stat().st_size // 1024} KB)")
    print(f"  机会 {s['total']} · GO {s['n_go']}（礼盒 {bc.get('gift-box', 0)} / 旅游 {bc.get('tourism', 0)}）"
          f" · 候选 {s['n_candidate']} · 观望 {s['n_hold']} · 空位红利均值 {s['void_dividend']}")
    if s["best"]:
        b = s["best"]
        print(f"  最佳机会: {b['query'][:34]}（{b['category_title']} · 可赢度 {b['score']}）")


if __name__ == "__main__":
    main()
