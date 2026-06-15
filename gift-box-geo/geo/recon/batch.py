"""批量侦察 runner：跑一个 segment 的所有 query → 存证据 → 汇总。

  python -m geo.recon.batch --segment A   # 中文，豆包联网真跑（需 ARK_* + 建议 ARK_BOT_ID）
  python -m geo.recon.batch --segment B   # 英文，mock 占位（待 Perplexity/OpenAI key）
"""
from __future__ import annotations

import argparse
import sys

from geo.adapters.doubao import DoubaoAdapter
from geo.adapters.mock import MockAdapter
from geo.config import REPO_ROOT, get_settings
from geo.evidence.schema import BuyerSegment, Capture
from geo.evidence.store import EvidenceStore
from geo.parsing import extract
from geo.recon.queries import queries_for_segment


def _build(settings):
    return EvidenceStore(settings.evidence_dir), extract.load_watchlist(settings.watchlist_path)


def _doubao_adapter(settings, store, watchlist) -> DoubaoAdapter:
    """构建豆包联网 adapter（require_search 保证带引用）。供全量/增量复用。"""
    settings.require_ark()
    return DoubaoAdapter(
        store,
        watchlist,
        min_interval_sec=settings.rate_limit_min_interval_sec,
        repo_root=REPO_ROOT,
        api_key=settings.ark_api_key,
        model=settings.ark_model,
        base_url=settings.ark_base_url,
        bot_id=settings.ark_bot_id,
        timeout=settings.http_timeout_sec,
        max_retries=settings.max_retries,
        require_search=bool(settings.ark_bot_id),
        search_retries=2,
    )


def _missing_a_queries(store):
    """无对应 capture 的 segment-A query（增量侦察：只跑没跑过的，避免重复/重复计数）。"""
    done = {c.query for c in store.load_all() if c.buyer_segment == BuyerSegment.A}
    return [q for q in queries_for_segment(BuyerSegment.A) if q.text not in done]


def run_segment_a(settings, store, watchlist, only_missing: bool = False) -> list[Capture]:
    """Segment A 中文：豆包联网真跑。only_missing=True 仅跑尚无证据的 query（增量）。"""
    doubao = _doubao_adapter(settings, store, watchlist)
    qs = _missing_a_queries(store) if only_missing else queries_for_segment(BuyerSegment.A)
    if not qs:
        print("（segment A 已无待跑 query）")
        return []
    return _run(doubao, qs, store, label="豆包·联网")


def run_segment_b_mock(settings, store, watchlist) -> list[Capture]:
    """Segment B 英文：mock 占位（明确标注非真证据）。"""
    mock = MockAdapter(
        store, watchlist, min_interval_sec=0, repo_root=REPO_ROOT, engine_label="mock-perplexity"
    )
    return _run(mock, queries_for_segment(BuyerSegment.B), store, label="mock·占位")


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
        brands = cap.named_brands or "—"
        print(f"[{label} {i}/{len(qs)}] 引用={len(cap.cited_sources):<2} 品牌={brands}  {q.text}")
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
    print(f"  空位(零品牌)   : {sum(1 for c in caps if not c.named_brands)}/{len(caps)}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="GEO 批量侦察")
    ap.add_argument("--segment", choices=["A", "B"], required=True, help="A=中文豆包真跑 / B=英文 mock")
    ap.add_argument(
        "--only-missing",
        action="store_true",
        help="仅跑尚无证据的 query（增量侦察，避免重复花钱/重复计数）。仅 segment A。",
    )
    args = ap.parse_args(argv)

    settings = get_settings()
    store, watchlist = _build(settings)
    if args.segment == "A":
        caps = run_segment_a(settings, store, watchlist, only_missing=args.only_missing)
    else:
        caps = run_segment_b_mock(settings, store, watchlist)
    _summary(caps)
    return 0


if __name__ == "__main__":
    sys.exit(main())
