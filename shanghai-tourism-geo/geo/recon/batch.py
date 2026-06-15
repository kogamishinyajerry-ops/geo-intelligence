"""批量侦察 runner：跑一个 segment 的所有 query → 存证据 → 汇总。

  python -m geo.recon.batch --segment A   # 外地客，豆包基础模型真跑（需 ARK_*）
  python -m geo.recon.batch --segment C   # 本地客，豆包基础模型真跑
  python -m geo.recon.batch --segment B --only-missing  # 入境客（英文），增量

⚠️ 用**普通 /chat/completions 接口**（bot_id=None）：联网(bots)接口有日配额墙(429)，
   且旅游 GEO 的核心信号 = 豆包答案里**推荐了哪些景点**（基础模型即给），引用源是次要情报。
   联网配额恢复后可另跑一轮带引用的补充侦察。
"""
from __future__ import annotations

import argparse
import sys

from geo.adapters.doubao import DoubaoAdapter
from geo.config import REPO_ROOT, get_settings
from geo.evidence.schema import BuyerSegment, Capture
from geo.evidence.store import EvidenceStore
from geo.parsing import extract
from geo.recon.queries import queries_for_segment


def _build(settings):
    return EvidenceStore(settings.evidence_dir), extract.load_watchlist(settings.watchlist_path)


def _doubao_adapter(settings, store, watchlist) -> DoubaoAdapter:
    """豆包**基础模型** adapter（bot_id=None → 普通 /chat/completions，绕开联网配额墙）。"""
    settings.require_ark()
    return DoubaoAdapter(
        store,
        watchlist,
        min_interval_sec=settings.rate_limit_min_interval_sec,
        repo_root=REPO_ROOT,
        api_key=settings.ark_api_key,
        model=settings.ark_model,
        base_url=settings.ark_base_url,
        bot_id=None,  # 强制普通接口（联网 bots 接口 429 配额墙）
        timeout=settings.http_timeout_sec,
        max_retries=settings.max_retries,
        require_search=False,
    )


def _missing_queries(store, seg: BuyerSegment):
    """无对应 capture 的 query（增量侦察：只跑没跑过的，避免重复/重复计数）。"""
    done = {c.query for c in store.load_all() if c.buyer_segment == seg}
    return [q for q in queries_for_segment(seg) if q.text not in done]


def run_segment(settings, store, watchlist, seg: BuyerSegment, only_missing: bool = False) -> list[Capture]:
    """任一客群：豆包基础模型真跑。only_missing=True 仅跑尚无证据的 query（增量）。"""
    doubao = _doubao_adapter(settings, store, watchlist)
    qs = _missing_queries(store, seg) if only_missing else queries_for_segment(seg)
    if not qs:
        print(f"（segment {seg.value} 已无待跑 query）")
        return []
    return _run(doubao, qs, store, label=f"豆包·基础·{seg.value}")


def _run(adapter, qs, store, *, label: str) -> list[Capture]:
    """逐条侦察并即时存档（partial-progress 安全）。

    单条失败不再让整批崩溃：
      - 撞配额墙（429 退避后仍失败）→ 优雅停止，已存的保留，余下 `--only-missing` 续跑；
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
                    f"已存 {len(caps)} 条；余下 {len(qs) - i + 1} 条 `--only-missing` 续跑。"
                )
                break
            print(f"[{label} {i}/{len(qs)}] ❌ HTTP {e.response.status_code if e.response else '?'} 跳过：{q.text}")
            continue
        except Exception as e:  # noqa: BLE001 — 单条容错，不让一条坏 query 拖垮整批
            print(f"[{label} {i}/{len(qs)}] ❌ {type(e).__name__} 跳过：{q.text}")
            continue
        store.save(cap)
        caps.append(cap)
        ents = cap.named_brands or "—（空位信号）"
        print(f"[{label} {i}/{len(qs)}] 景点={ents}  «{q.text}»")
    return caps


def _summary(caps: list[Capture]) -> None:
    if not caps:
        print("（无 capture）")
        return
    real = [c for c in caps if not c.is_mock]
    print("\n── 批量侦察汇总 ──")
    print(f"  captures      : {len(caps)}（真实 {len(real)} / mock {len(caps) - len(real)}）")
    print(f"  命中景点的     : {sum(1 for c in caps if c.named_brands)}/{len(caps)}")
    print(f"  空位(零景点)   : {sum(1 for c in caps if not c.named_brands)}/{len(caps)}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="上海旅游 GEO 批量侦察")
    ap.add_argument("--segment", choices=["A", "B", "C"], required=True,
                    help="A=外地客 / B=入境客(英文) / C=本地客，均豆包基础模型真跑")
    ap.add_argument("--only-missing", action="store_true",
                    help="仅跑尚无证据的 query（增量侦察，避免重复花钱/重复计数）。")
    args = ap.parse_args(argv)

    settings = get_settings()
    store, watchlist = _build(settings)
    caps = run_segment(settings, store, watchlist, BuyerSegment(args.segment), only_missing=args.only_missing)
    _summary(caps)
    return 0


if __name__ == "__main__":
    sys.exit(main())
