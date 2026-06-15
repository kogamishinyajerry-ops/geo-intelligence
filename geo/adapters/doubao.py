"""豆包 adapter — 火山方舟（Volcengine Ark）。

- 普通模型：/chat/completions，拿 raw_answer。
- 配了 ARK_BOT_ID（联网应用）：走 /bots/chat/completions，回答带联网引用。
  引用从 bot_usage...results[] 抽取，含 url/title/site_name + 权威/相关/时效分（GEO 富信号）。
实测确认（2026-06-14）：方舟联网 API **不返回商品卡**（抖音商城商品卡是豆包 C 端特性）
  → product_cards 通常为空。要测商品卡需走 C 端 App（另一条监测线）。
原始 HTTP 响应体整体归档为不可篡改证据（红线 #1）。
"""
from __future__ import annotations

import json
from urllib.parse import urlparse

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from geo.adapters.base import EngineAdapter, RawResult
from geo.evidence.schema import BuyerSegment, CitedSource, ProductCard


def _is_retryable(exc: Exception) -> bool:
    """重试瞬时错误：传输错误 + 5xx + 429（限流，退避后重试）。
    其余 4xx（鉴权/模型未开通/参数错）重试无意义，直接抛。"""
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code >= 500 or code == 429  # 429=Too Many Requests，本就是"慢点再来"的信号
    return False


class DoubaoAdapter(EngineAdapter):
    name = "doubao"
    is_mock = False

    def __init__(
        self,
        *args,
        api_key: str,
        model: str,
        base_url: str,
        bot_id: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        require_search: bool = False,
        search_retries: int = 2,
        **kw,
    ):
        super().__init__(*args, **kw)
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.bot_id = bot_id
        self.timeout = timeout
        self.max_retries = max_retries
        self.require_search = require_search  # bot 模式下要求联网触发（非确定性 → 重试）
        self.search_retries = search_retries

    def _endpoint(self) -> str:
        return (
            f"{self.base_url}/bots/chat/completions"
            if self.bot_id
            else f"{self.base_url}/chat/completions"
        )

    def _post(self, query: str) -> dict:
        payload = {
            "model": self.bot_id or self.model,
            "messages": [{"role": "user", "content": query}],
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=20),
            retry=retry_if_exception(_is_retryable),
            reraise=True,
        )
        def _call() -> httpx.Response:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(self._endpoint(), headers=headers, json=payload)
                resp.raise_for_status()
                return resp

        return _call().json()

    def query(self, query: str, buyer_segment: BuyerSegment) -> RawResult:
        # 联网非确定性：bot 模式下若没触发搜索（action_details 空）→ 重试拿引用。
        want_search = self.require_search and bool(self.bot_id)
        attempts = 1 + (self.search_retries if want_search else 0)
        result: RawResult | None = None
        for i in range(attempts):
            data = self._post(query)
            try:
                answer = data["choices"][0]["message"]["content"] or ""
            except (KeyError, IndexError, TypeError):
                answer = ""
            result = RawResult(
                answer=answer,
                raw_payload=json.dumps(data, ensure_ascii=False, indent=2),
                engine_model=data.get("model") or self.bot_id or self.model,
                request_params={
                    "endpoint": self._endpoint(),
                    "model": self.bot_id or self.model,
                    "attempt": i + 1,
                },
                cited_sources=_parse_references(data),
                product_cards=_parse_product_cards(data),
            )
            searched = bool((data.get("bot_usage") or {}).get("action_details"))
            if not want_search or searched:
                break
        return result


def _parse_references(data: dict) -> list[CitedSource]:
    """从联网插件搜索结果抽取引用（GEO 核心信号）。

    主源：bot_usage.action_details[].tool_details[].output.data.data.results[]
          —— 含 url/title/site_name + search_plugin_data 的 auth/rel/freshness 分。
    兜底：顶层 references[]（仅 url）。去重按 url、保序。
    """
    out: list[CitedSource] = []
    seen: set[str] = set()
    for action in (data.get("bot_usage") or {}).get("action_details") or []:
        for tool in action.get("tool_details") or []:
            output = tool.get("output") or {}
            results = (((output.get("data") or {}).get("data") or {}).get("results")) or []
            for res in results:
                if not isinstance(res, dict):
                    continue
                url = res.get("url")
                if not url or url in seen:
                    continue
                seen.add(url)
                spd = res.get("search_plugin_data") or {}
                try:
                    domain = urlparse(url).netloc or None
                except Exception:
                    domain = None
                out.append(
                    CitedSource(
                        url=url,
                        title=res.get("title"),
                        domain=domain,
                        site_name=res.get("site_name"),
                        auth_score=spd.get("auth_score"),
                        rel_score=spd.get("rel_score"),
                        freshness_score=spd.get("freshness_score"),
                    )
                )
    if not out:  # 兜底：顶层 references[]
        for ref in data.get("references") or []:
            if isinstance(ref, dict):
                url = ref.get("url") or ref.get("link")
            elif isinstance(ref, str):
                url = ref
            else:
                url = None
            if url and url not in seen:
                seen.add(url)
                out.append(CitedSource(url=url))
    return out


def _parse_product_cards(data: dict) -> list[ProductCard]:
    """商品卡防御式抽取。实测：方舟联网 API 不返回商品卡 → 通常为空（见模块 docstring）。"""
    cards: list = []
    try:
        msg = data["choices"][0]["message"]
        cards = msg.get("product_cards") or msg.get("products") or msg.get("goods") or []
    except (KeyError, IndexError, TypeError):
        cards = []

    out: list[ProductCard] = []
    for c in cards or []:
        if not isinstance(c, dict):
            continue
        title = c.get("title") or c.get("name")
        if not title:
            continue
        out.append(
            ProductCard(
                title=title,
                platform=c.get("platform") or c.get("source"),
                shop=c.get("shop") or c.get("shop_name"),
                price=None if c.get("price") is None else str(c.get("price")),
                rating=None if c.get("rating") is None else str(c.get("rating")),
                url=c.get("url") or c.get("link"),
            )
        )
    return out
