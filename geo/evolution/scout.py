"""Scout CLI · 一手信号侦查（proposal-only）。

  GEO_CATEGORY=gift-box python -m geo.evolution.scout --signals s2,s5
  ... --dry-run   # 只打印，不落 intel 文件

铁律：proposal-only——只产 EvolutionIntel(恒 PROPOSED) 写 evolution/intel/<pkg>/；
绝不改 watchlist/queries/category/adapter，绝不发布、绝不花钱（一手信号零外部依赖）。
台账坏则 fail-closed 拒跑（不在坏地基上侦查）。
"""
from __future__ import annotations

import argparse
import sys

_VALID_SIGNALS = {"s2", "s5"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="GEO 演化侦查 Scout（一手信号，proposal-only）")
    ap.add_argument("--signals", default="s2,s5", help="逗号分隔，可选 s2,s5（默认全跑）")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不写 intel 文件")
    ap.add_argument("--baseline-rate", type=float, default=None, help="S2 联网抽取命中率历史基线（缺则只记录不报警）")
    args = ap.parse_args(argv)

    signals = [s.strip() for s in args.signals.split(",") if s.strip()]
    unknown = [s for s in signals if s not in _VALID_SIGNALS]
    if unknown:
        print(f"⛔ 未知信号 {unknown}（可选 {sorted(_VALID_SIGNALS)}）", file=sys.stderr)
        return 2  # fail-closed

    from geo.category import active_profile
    from geo.evolution.assumptions import load_assumptions, validate_assumptions

    prof = active_profile()
    print(f"🛰️  Scout · 品类={prof.key}（pkg={prof.pkg}） · 信号={signals}")

    # 台账校验：坏地基不侦查（fail-closed）
    try:
        rows = load_assumptions(prof.pkg)
    except FileNotFoundError as e:
        print(f"⛔ {e}", file=sys.stderr)
        return 2
    errors = validate_assumptions(rows)
    if errors:
        print("⛔ 冻结假设台账校验失败（拒绝在坏地基上侦查）：", file=sys.stderr)
        for e in errors:
            print(f"   {e}", file=sys.stderr)
        return 2
    print(f"   冻结假设台账：{len(rows)} 条（{sum(1 for r in rows if r.get('status') == 'at-risk')} 条 at-risk）")

    intels = []
    if "s2" in signals:
        from geo.evolution.signals.s2_structure import run_s2

        s2 = run_s2(baseline_rate=args.baseline_rate)
        if not s2 and not prof.use_search:
            print("   [S2] 不适用：该品类 use_search=False，零引用是设计基线（不报漂移）。")
        elif not s2:
            print("   [S2] 无结构漂移信号（或无基线/样本不足）。")
        intels += s2
    if "s5" in signals:
        from geo.evolution.signals.s5_candidates import discover_candidates

        s5 = discover_candidates()
        intels += s5
        if not s5:
            print("   [S5] 无 watchlist 外候选（≥3 复现）。")

    store = None
    if not args.dry_run:
        from geo.evolution.store import IntelStore, intel_dir_for_active

        store = IntelStore(intel_dir_for_active())

    print(f"\n── 演化情报 {len(intels)} 条{'（dry-run，未落盘）' if args.dry_run else ''} ──")
    for it in intels:
        loc = ""
        if store is not None:
            loc = f" → {store.save(it).name}"
        codex = "（需 Codex 异源审）" if it.proposed_change.get("requires_codex_review") else ""
        print(f"  [{it.signal_layer}] {it.confidence} · {it.claim}")
        print(f"        接缝={it.proposed_change['target_seam']} · 证据 {len(it.evidence['internal'])} 条{codex}{loc}")

    print("\nproposal-only：本次未改任何系统配置 / watchlist，全部 hitl_status=PROPOSED，待 HITL 人审。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
