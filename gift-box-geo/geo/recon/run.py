"""Recon driver (CLI).

  python -m geo.recon.run --mock-only   # 无需任何 key，跑通全管道（证明管道为真）
  python -m geo.recon.run --phase0      # 中文豆包真跑 + 英文 mock 占位（需 ARK_* 凭证）
"""
from __future__ import annotations

import argparse
import sys

from geo.adapters.doubao import DoubaoAdapter
from geo.adapters.mock import MockAdapter
from geo.config import REPO_ROOT, get_settings
from geo.evidence.store import EvidenceStore
from geo.parsing import extract
from geo.recon.queries import phase0_slice


def _build(settings):
    store = EvidenceStore(settings.evidence_dir)
    watchlist = extract.load_watchlist(settings.watchlist_path)
    return store, watchlist


def _summary(cap) -> str:
    brands = cap.named_brands or "—（无观察名单品牌 → 空位信号）"
    return "\n".join(
        [
            f"  id            : {cap.id}",
            f"  engine        : {cap.engine}  (mock={cap.is_mock}, model={cap.engine_model})",
            f"  segment       : {cap.buyer_segment.value}",
            f"  query         : {cap.query}",
            f"  named_brands  : {brands}",
            f"  cited_sources : {len(cap.cited_sources)}",
            f"  product_cards : {len(cap.product_cards)}",
            f"  links         : {len(cap.links)}",
            f"  raw_capture   : {cap.raw_capture_path}",
            f"  answer[:240]  : {cap.raw_answer[:240].strip()!r}",
        ]
    )


def _save_and_report(store, cap, label: str) -> None:
    path = store.save(cap)
    print(f"[{label}] {cap.query}")
    print(_summary(cap))
    print(f"  saved         : {path.relative_to(REPO_ROOT)}\n")


def run_phase0() -> int:
    settings = get_settings()
    store, watchlist = _build(settings)
    sl = phase0_slice()

    # 中文：豆包真跑（缺凭证则明确报错，不静默回退假数据）
    settings.require_ark()
    doubao = DoubaoAdapter(
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
    )
    zh = sl["zh"]
    _save_and_report(store, doubao.run(zh.text, zh.buyer_segment), "豆包·真实")

    # 英文：mock 占位（明确标注非真证据）
    en = sl["en"]
    mock = MockAdapter(
        store, watchlist, min_interval_sec=0, repo_root=REPO_ROOT, engine_label="mock-perplexity"
    )
    _save_and_report(store, mock.run(en.text, en.buyer_segment), "mock·占位")
    return 0


def run_mock_only() -> int:
    settings = get_settings()
    store, watchlist = _build(settings)
    sl = phase0_slice()
    for key, label in (("zh", "mock-doubao"), ("en", "mock-perplexity")):
        q = sl[key]
        mock = MockAdapter(
            store, watchlist, min_interval_sec=0, repo_root=REPO_ROOT, engine_label=label
        )
        _save_and_report(store, mock.run(q.text, q.buyer_segment), label)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="GEO recon driver")
    ap.add_argument("--phase0", action="store_true", help="中文豆包真跑 + 英文 mock（需 ARK_* 凭证）")
    ap.add_argument("--mock-only", action="store_true", help="全 mock 跑通管道（无需 key）")
    args = ap.parse_args(argv)
    if args.mock_only:
        return run_mock_only()
    if args.phase0:
        return run_phase0()
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
