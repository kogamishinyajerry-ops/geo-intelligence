"""Deterministic, reproducible extraction (红线 #2).

品牌抽取只匹配 watchlist 词条；链接用正则；引用优先取引擎结构化字段，否则从链接派生。
全部确定性 —— 同一 raw_answer 跑两次结果一致。不在证据层用 LLM 做 NER。
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import yaml

from geo.evidence.schema import CitedSource

# BuyerSegment.value → watchlist 段 key（旅游：实体=景点名，非品牌）
SEGMENT_WATCHLIST_KEY: dict[str, str] = {
    "A": "segment_A_domestic",  # 外地国内游客
    "B": "segment_B_inbound",  # 入境外籍游客
    "C": "segment_C_local",  # 本地客
}

# 链接：到空白或常见中英文闭合标点为止
URL_RE = re.compile(r"https?://[^\s\)\]\}\>，。；！？\"'）】、]+")
_TRAILING = ".,;:)]}。，；！？、"


def extract_links(text: str) -> list[str]:
    """去重、保序地抽取 URL；剥离尾随标点。"""
    seen: set[str] = set()
    out: list[str] = []
    for m in URL_RE.findall(text or ""):
        u = m.rstrip(_TRAILING)
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def links_to_sources(links: list[str]) -> list[CitedSource]:
    out: list[CitedSource] = []
    for u in links:
        try:
            dom = urlparse(u).netloc or None
        except Exception:
            dom = None
        out.append(CitedSource(url=u, domain=dom))
    return out


def load_watchlist(path: Path | str) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _terms(watchlist: dict, segment_key: str | None) -> list[tuple[str, list[str]]]:
    keys = [segment_key] if segment_key else list(watchlist.keys())
    entries: list[tuple[str, list[str]]] = []
    for k in keys:
        for item in watchlist.get(k) or []:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not name:
                continue
            entries.append((name, item.get("aliases") or [name]))
    return entries


def extract_brands(text: str, watchlist: dict, segment_key: str | None = None) -> list[str]:
    """证据级品牌抽取：只匹配 watchlist，返回按首次出现排序的 canonical name（去重）。
    named_brands[0] = 首个被提及 → 首选推荐率的依据。"""
    text_l = (text or "").lower()
    hits: list[tuple[int, str]] = []
    for name, terms in _terms(watchlist, segment_key):
        first: int | None = None
        for t in terms:
            idx = text_l.find(t.lower())
            if idx != -1 and (first is None or idx < first):
                first = idx
        if first is not None:
            hits.append((first, name))
    hits.sort(key=lambda x: x[0])
    out: list[str] = []
    seen: set[str] = set()
    for _, name in hits:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out
