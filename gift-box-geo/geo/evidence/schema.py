"""Evidence schema (§5) — LOCKED.

每条 capture = 一条 AI 回答的存档证据。所有指标（占答率/提及率/首选推荐率/空位评分）
都是对本表的**纯函数**（见 geo/metrics）；禁止旁路、禁止凭模型印象编数字（红线 #1）。

相对 brief §5 的最小扩展（brief 写明 "至少含"，故允许）：
  - raw_capture_path : API adapter 没有截图，改归档原始响应体作为不可篡改证据
  - is_mock          : 诚实标注，mock 数据绝不冒充真证据
  - engine_model / request_params / schema_version / parser_version : 可复现审计字段
named_brands 用 list[str] 并**按首次出现排序**（[0] = 首个被提及 → 首选推荐率依据）。
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

SCHEMA_VERSION = "0.2.0"  # 0.2.0: CitedSource 增 site_name + auth/rel/freshness 分（联网引用富信号）


class BuyerSegment(str, Enum):
    A = "A"  # 中国人买来送老外客户 → 中文 AI + 抖音/淘宝货架
    B = "B"  # 老外自己买 → 英文 AI + Shopify


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    UNSCORED = "unscored"  # 诚实：无法可靠判定时不编（红线 #1）；Phase 2 再上可辩护的分类器


class CitedSource(BaseModel):
    url: str
    title: Optional[str] = None
    domain: Optional[str] = None
    site_name: Optional[str] = None
    # 联网引用的 GEO 富信号（火山方舟 search_plugin_data）——决定"为何被引用 / 权威是否复利"
    auth_score: Optional[float] = None  # 权威度
    rel_score: Optional[float] = None  # 相关度
    freshness_score: Optional[float] = None  # 时效性


class ProductCard(BaseModel):
    title: str
    platform: Optional[str] = None  # 抖音商城 / 天猫 / Shopify ...
    shop: Optional[str] = None
    price: Optional[str] = None  # 保留原文字符串，不强转数字（保真）
    rating: Optional[str] = None
    url: Optional[str] = None


class Capture(BaseModel):
    # ── 身份 / 可复现 ──
    id: str
    schema_version: str = SCHEMA_VERSION
    engine: str
    engine_model: Optional[str] = None
    query: str
    buyer_segment: BuyerSegment
    timestamp: datetime  # 强制 UTC

    # ── 原始证据（不可篡改）──
    raw_answer: str
    raw_capture_path: Optional[str] = None  # 归档的原始 API 响应体（相对仓库根）
    screenshot_path: Optional[str] = None  # 浏览器 adapter 用；API adapter 为空
    is_mock: bool = False  # 诚实标注

    # ── 解析派生（全部可回溯 raw_answer / raw_capture）──
    named_brands: list[str] = Field(default_factory=list)  # 按首次出现排序
    cited_sources: list[CitedSource] = Field(default_factory=list)
    product_cards: list[ProductCard] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    sentiment: Sentiment = Sentiment.UNSCORED

    # ── 审计 ──
    request_params: dict = Field(default_factory=dict)
    parser_version: str = SCHEMA_VERSION

    @field_validator("timestamp")
    @classmethod
    def _force_utc(cls, v: datetime) -> datetime:
        return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v.astimezone(timezone.utc)

    @staticmethod
    def make_id(
        engine: str, buyer_segment: "str | BuyerSegment", ts: datetime, raw_answer: str
    ) -> str:
        """可读 + 可去重的 id：{engine}-{segment}-{utc}-{sha10(raw_answer)}。
        相同回答内容产生相同的 hash 段，便于检测重复抓取。"""
        seg = buyer_segment.value if isinstance(buyer_segment, BuyerSegment) else str(buyer_segment)
        digest = hashlib.sha256(raw_answer.encode("utf-8")).hexdigest()[:10]
        ts_utc = ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts.astimezone(timezone.utc)
        stamp = ts_utc.strftime("%Y%m%dT%H%M%SZ")
        return f"{engine}-{seg}-{stamp}-{digest}"
