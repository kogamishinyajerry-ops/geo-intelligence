"""EngineAdapter base — 统一 query()->capture()->parse() + 限速。

新增引擎 = 加一个子类实现 query()，不动主流程（brief §3）。
capture 编排（归档原始响应 + 确定性解析 + 组装 Capture）在基类做，子类只管打引擎。
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from geo.evidence.schema import BuyerSegment, Capture, CitedSource, ProductCard
from geo.evidence.store import EvidenceStore
from geo.parsing import extract


@dataclass
class RawResult:
    """子类 query() 的返回：原始回答 + 原始响应体(归档用) + 引擎给的结构化字段。"""

    answer: str
    raw_payload: str
    engine_model: str | None = None
    request_params: dict = field(default_factory=dict)
    cited_sources: list[CitedSource] = field(default_factory=list)
    product_cards: list[ProductCard] = field(default_factory=list)


class EngineAdapter(ABC):
    name: str = "base"
    is_mock: bool = False

    def __init__(
        self,
        store: EvidenceStore,
        watchlist: dict,
        *,
        min_interval_sec: float = 1.5,
        repo_root: Path | None = None,
    ):
        self.store = store
        self.watchlist = watchlist
        self.min_interval_sec = min_interval_sec
        self.repo_root = repo_root
        self._last_call = 0.0

    def _rate_limit(self) -> None:
        if self.min_interval_sec <= 0:
            return
        wait = self.min_interval_sec - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    @abstractmethod
    def query(self, query: str, buyer_segment: BuyerSegment) -> RawResult:
        """命中引擎，返回原始回答 + 原始响应体。子类实现。"""

    def run(self, query: str, buyer_segment: BuyerSegment) -> Capture:
        """端到端一条：限速 -> query -> 归档原始 -> 确定性解析 -> Capture。"""
        self._rate_limit()
        result = self.query(query, buyer_segment)
        ts = datetime.now(timezone.utc)
        cap_id = Capture.make_id(self.name, buyer_segment, ts, result.answer)

        raw_path = self.store.archive_raw(cap_id, result.raw_payload, suffix=".json")
        rel_raw = (
            str(raw_path.relative_to(self.repo_root)) if self.repo_root else str(raw_path)
        )

        seg_key = extract.segment_watchlist_key(buyer_segment.value)
        links = extract.extract_links(result.answer)
        brands = extract.extract_brands(result.answer, self.watchlist, seg_key)
        sources = result.cited_sources or extract.links_to_sources(links)

        return Capture(
            id=cap_id,
            engine=self.name,
            engine_model=result.engine_model,
            query=query,
            buyer_segment=buyer_segment,
            timestamp=ts,
            raw_answer=result.answer,
            raw_capture_path=rel_raw,
            is_mock=self.is_mock,
            named_brands=brands,
            cited_sources=sources,
            product_cards=result.product_cards,
            links=links,
            request_params=result.request_params,
        )
