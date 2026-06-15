"""Mock adapter — 英文侧凭证到位前的占位。

is_mock=True 会写进每条 Capture；raw_answer 带 [MOCK] 前缀。**绝不冒充真证据**（红线 #1）。
作用：在没有任何 key 时也能跑通 query->capture->parse->metrics 全管道，验证管道为真。
"""
from __future__ import annotations

import json

from geo.adapters.base import EngineAdapter, RawResult
from geo.evidence.schema import BuyerSegment


class MockAdapter(EngineAdapter):
    name = "mock"
    is_mock = True

    def __init__(self, *args, canned: dict[str, str] | None = None, engine_label: str = "mock", **kw):
        super().__init__(*args, **kw)
        self.canned = canned or {}
        self.name = engine_label  # 例如 "mock-perplexity"

    def query(self, query: str, buyer_segment: BuyerSegment) -> RawResult:
        answer = self.canned.get(query) or _default_canned(query, buyer_segment)
        payload = json.dumps(
            {"_mock": True, "query": query, "segment": buyer_segment.value, "answer": answer},
            ensure_ascii=False,
            indent=2,
        )
        return RawResult(
            answer=answer,
            raw_payload=payload,
            engine_model="mock",
            request_params={"mock": True},
        )


def _default_canned(query: str, seg: BuyerSegment) -> str:
    return (
        f"[MOCK ANSWER — 非真实证据] 针对「{query}」的占位回答。"
        "英文引擎（Perplexity / OpenAI）凭证到位后，此处即为真实 AI 回答。"
        "示例提到 Harry & David 和 Williams Sonoma 作为高端礼盒选择，"
        "并附 https://www.harryanddavid.com 供管道演示。"
    )
