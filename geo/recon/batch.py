"""批量侦察 runner：跑一个 segment 的所有 query → 存证据 → 汇总。

品类无关：segment 选项、real/mock 分派、联网与否全部由 active profile 决定。

  GEO_CATEGORY=gift-box python -m geo.recon.batch --segment A   # 中文豆包联网真跑
  GEO_CATEGORY=tourism  python -m geo.recon.batch --segment A   # 普通接口真跑（零联网引用）
"""
from __future__ import annotations

import argparse
import sys

from geo.adapters.doubao import DoubaoAdapter
from geo.adapters.mock import MockAdapter
from geo.category import active_profile
from geo.config import SpendNotAuthorizedError, get_settings, require_spend
from geo.evidence.schema import BuyerSegment, Capture
from geo.evidence.store import EvidenceStore
from geo.parsing import extract
from geo.recon.queries import queries_for_segment


def _build(settings):
    return EvidenceStore(settings.evidence_dir), extract.load_watchlist(settings.watchlist_path)


def _doubao_adapter(settings, store, watchlist) -> DoubaoAdapter:
    """构建豆包 adapter。是否联网由 active profile.use_search 决定：
    use_search → 走 /bots（require_search 保证带引用）；否则普通接口（bot_id=None）。"""
    require_spend()  # 真打付费引擎前硬门控（fail-closed，红线 §3）；mock 段不经此函数
    settings.require_ark()
    prof = active_profile()
    if prof.use_search:
        bot_id = settings.ark_bot_id
        require_search = bool(settings.ark_bot_id)
    else:
        bot_id = None
        require_search = False
    return DoubaoAdapter(
        store,
        watchlist,
        min_interval_sec=settings.rate_limit_min_interval_sec,
        repo_root=settings.category_root,
        api_key=settings.ark_api_key,
        model=settings.ark_model,
        base_url=settings.ark_base_url,
        bot_id=bot_id,
        timeout=settings.http_timeout_sec,
        max_retries=settings.max_retries,
        require_search=require_search,
        search_retries=2,
    )


def _missing(store, seg: BuyerSegment):
    """无对应 capture 的 query（增量侦察：只跑没跑过的，避免重复/重复计数）。"""
    done = {c.query for c in store.load_all() if c.buyer_segment == seg}
    return [q for q in queries_for_segment(seg) if q.text not in done]


def run_segment(
    settings, store, watchlist, seg: BuyerSegment, only_missing: bool = False
) -> list[Capture]:
    """通用单段侦察。mock 段（seg ∈ profile.mock_segments）用 MockAdapter，否则 DoubaoAdapter。
    only_missing=True 仅跑尚无证据的 query（增量）。"""
    prof = active_profile()
    if seg.value in prof.mock_segments:
        adapter = MockAdapter(
            store,
            watchlist,
            min_interval_sec=0,
            repo_root=settings.category_root,
            engine_label="mock-perplexity",
        )
        label = "mock·占位"
    else:
        adapter = _doubao_adapter(settings, store, watchlist)
        label = "豆包·联网" if prof.use_search else "豆包·普通"

    qs = _missing(store, seg) if only_missing else queries_for_segment(seg)
    if not qs:
        print(f"（segment {seg.value} 已无待跑 query）")
        return []
    return _run(adapter, qs, store, label=label)


def _run(adapter, qs, store, *, label: str) -> list[Capture]:
    """逐条侦察并即时存档（partial-progress 安全）。

    单条失败不再让整批崩溃：
      - 撞配额墙（429 退避后仍失败）→ 优雅停止，已存的保留，余下明日 `--only-missing` 续跑；
      - 其它异常 → 跳过该 query、继续下一条。
    """
    import httpx

    caps: list[Capture] = []
    for i, q in enumerate(qs, 1):
        try:
            cap = adapter.run(q.text, q.buyer_segment)
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code == 429:
                print(
                    f"[{label} {i}/{len(qs)}] ⚠️ 429 配额墙（退避后仍限流）→ 停止本批，"
                    f"已存 {len(caps)} 条；余下 {len(qs) - i + 1} 条明日 `--only-missing` 续跑。"
                )
                break
            print(f"[{label} {i}/{len(qs)}] ❌ HTTP {e.response.status_code if e.response else '?'} 跳过：{q.text}")
            continue
        except Exception as e:  # noqa: BLE001 — 单条容错，不让一条坏 query 拖垮整批
            print(f"[{label} {i}/{len(qs)}] ❌ {type(e).__name__} 跳过：{q.text}")
            continue
        store.save(cap)
        caps.append(cap)
        ents = cap.named_brands or "—"
        print(f"[{label} {i}/{len(qs)}] 引用={len(cap.cited_sources):<2} 命中实体={ents}  {q.text}")
    return caps


def _summary(caps: list[Capture]) -> None:
    if not caps:
        print("（无 capture）")
        return
    real = [c for c in caps if not c.is_mock]
    with_cites = [c for c in caps if c.cited_sources]
    print("\n── 批量侦察汇总 ──")
    print(f"  captures      : {len(caps)}（真实 {len(real)} / mock {len(caps) - len(real)}）")
    print(f"  带引用的       : {len(with_cites)}/{len(caps)}")
    print(f"  总引用条数     : {sum(len(c.cited_sources) for c in caps)}")
    print(f"  空位(零命中实体): {sum(1 for c in caps if not c.named_brands)}/{len(caps)}")


def main(argv=None) -> int:
    prof = active_profile()
    ap = argparse.ArgumentParser(description="GEO 批量侦察")
    ap.add_argument(
        "--segment",
        choices=list(prof.segments),
        required=True,
        help=f"侦察段（real={list(prof.real_segments)} / mock={list(prof.mock_segments)}）",
    )
    ap.add_argument(
        "--only-missing",
        action="store_true",
        help="仅跑尚无证据的 query（增量侦察，避免重复花钱/重复计数）。",
    )
    args = ap.parse_args(argv)

    settings = get_settings()
    seg = BuyerSegment(args.segment)
    # real 段真打付费引擎：花钱闸前移到任何写盘/建目录之前（fail-closed，红线 §3）。
    if seg.value not in prof.mock_segments:
        try:
            require_spend()
        except SpendNotAuthorizedError as e:
            print(str(e))
            return 2  # 花钱被拒（区别于 require_ark 缺凭证的 RuntimeError 冒泡）
    store, watchlist = _build(settings)
    try:
        caps = run_segment(settings, store, watchlist, seg, only_missing=args.only_missing)
    except SpendNotAuthorizedError as e:  # 防御：_doubao_adapter 内仍有 require_spend（双门）
        print(str(e))
        return 2
    _summary(caps)
    return 0


if __name__ == "__main__":
    sys.exit(main())
