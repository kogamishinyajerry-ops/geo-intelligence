#!/usr/bin/env python3
"""统一机会指挥台 gatherer 的契约 + 红线测试。

可直接 `python3 test_opportunity_board.py`（零依赖；不需要 pytest）。
集成性质：build_unified() 会用两个 repo 各自的 venv 子进程真算 payload。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from opportunity_board import build_unified  # noqa: E402

CONTRACT_OPP_KEYS = {
    "category", "category_title", "entity_label", "query", "score", "go",
    "dividend", "reason", "action", "capture_ids",
}


def _check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def run() -> None:
    p = build_unified()

    # —— 形状 ——
    for k in ("meta", "summary", "opportunities", "evidence", "honesty"):
        _check(k in p, f"payload 缺顶层键 {k}")
    opps = p["opportunities"]
    _check(len(opps) > 0, "无机会")
    for o in opps:
        missing = CONTRACT_OPP_KEYS - set(o)
        _check(not missing, f"机会缺字段 {missing}: {o.get('query')}")

    # —— P0#2 双注册表→单 SSOT 回归网：引擎 _PROFILES 与展示 _DISPLAY key 不许漂移 ——
    from geo.category import all_profiles
    from opportunity_board import _DISPLAY, _categories
    engine_keys = {pp.key for pp in all_profiles()}
    _check(engine_keys == set(_DISPLAY), f"引擎/展示 key 漂移: engine={engine_keys} display={set(_DISPLAY)}")
    _check([c["key"] for c in _categories()] == [pp.key for pp in all_profiles()], "派生品类顺序与引擎不一致")
    meta_keys = {c["key"] for c in p["meta"]["categories"]}
    _check(meta_keys == engine_keys, f"看板渲染漏/多品类: meta={meta_keys} engine={engine_keys}")
    # fail-closed 守卫：_DISPLAY 缺某引擎品类 → _categories() 必须抛，拒绝静默漏渲染
    import opportunity_board as ob
    saved = dict(ob._DISPLAY)
    try:
        ob._DISPLAY = {k: v for k, v in saved.items() if k != next(iter(engine_keys))}
        try:
            ob._categories()
            _check(False, "_DISPLAY 缺品类时 _categories() 未 fail-closed")
        except RuntimeError:
            pass
    finally:
        ob._DISPLAY = saved

    # —— 排序：按 score 降序 ——
    scores = [o["score"] for o in opps]
    _check(scores == sorted(scores, reverse=True), "机会未按 score 降序")

    # —— 可回溯红线：每条机会 capture_ids 非空且全在 evidence ——
    ev = set(p["evidence"])
    for o in opps:
        _check(bool(o["capture_ids"]), f"机会无 capture_ids: {o['query']}")
        bad = [c for c in o["capture_ids"] if c not in ev]
        _check(not bad, f"机会 capture_id 不可回溯 {bad}: {o['query']}")

    # —— dividend 合法区间 ——
    for o in opps:
        _check(0.0 <= o["dividend"] <= 1.0, f"dividend 越界 {o['dividend']}: {o['query']}")

    # —— 诚实红线：跨品类评分语义披露在 caveats[0] ——
    _check(p["honesty"]["caveats"], "honesty.caveats 为空")
    _check("跨品类评分语义不同" in p["honesty"]["caveats"][0], "缺跨品类评分语义诚实披露")

    # —— summary 自洽 + 与逐 repo 求和一致（无编造）——
    s = p["summary"]
    _check(s["total"] == len(opps), "summary.total 不符")
    _check(s["n_go"] + s["n_candidate"] + s["n_hold"] == s["total"], "档位计数不自洽")
    cat_totals = {c["key"]: 0 for c in p["meta"]["categories"]}
    for o in opps:
        cat_totals[o["category"]] += 1
    _check(sum(cat_totals.values()) == s["total"], "品类机会数求和≠total")

    # —— action.kind 合法 ——
    for o in opps:
        _check(o["action"]["kind"] in {"draft", "produce", "consider", "hold"},
               f"非法 action.kind {o['action']['kind']}")

    # —— 渲染：render_html 真出含真值的自包含 HTML ——
    from opportunity_render import render_html
    html = render_html(p)
    _check("<style>" in html and "const DATA" in html, "render 输出非自包含 HTML")
    _check(len(html) > 50000, f"render 输出过短 {len(html)}")
    best_q = s["best"]["query"][:6]
    _check(best_q in html, "最佳机会未进 HTML")

    print(f"ALL PASS · 机会 {s['total']}（GO {s['n_go']} / 候选 {s['n_candidate']} / 观望 {s['n_hold']}）"
          f" · 品类 {cat_totals} · evidence {len(ev)} · html {len(html) // 1024}KB")


if __name__ == "__main__":
    try:
        run()
    except AssertionError as e:
        print(f"FAIL: {e}")
        sys.exit(1)
