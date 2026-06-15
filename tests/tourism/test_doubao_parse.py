from geo.adapters.doubao import _is_retryable, _parse_product_cards, _parse_references


def _bot_payload(results):
    return {
        "bot_usage": {
            "action_details": [
                {"name": "content_plugin", "tool_details": [
                    {"name": "search", "output": {"data": {"data": {"results": results}}}}
                ]}
            ]
        }
    }


def test_parse_references_rich_with_scores_and_dedup():
    results = [
        {"url": "https://a.com/x", "title": "T1", "site_name": "SiteA",
         "search_plugin_data": {"auth_score": 0.3, "rel_score": 1, "freshness_score": 1}},
        {"url": "https://b.com/y", "title": "T2", "site_name": "SiteB",
         "search_plugin_data": {"auth_score": 0.9}},
        {"url": "https://a.com/x", "title": "dup"},  # 同 url → 丢弃
    ]
    refs = _parse_references(_bot_payload(results))
    assert [r.url for r in refs] == ["https://a.com/x", "https://b.com/y"]
    assert refs[0].site_name == "SiteA" and refs[0].domain == "a.com"
    assert refs[0].auth_score == 0.3 and refs[0].rel_score == 1 and refs[0].freshness_score == 1
    assert refs[1].auth_score == 0.9 and refs[1].rel_score is None


def test_parse_references_fallback_toplevel():
    data = {"references": [{"url": "https://c.com"}, "https://d.com"]}
    refs = _parse_references(data)
    assert [r.url for r in refs] == ["https://c.com", "https://d.com"]


def test_parse_references_empty():
    assert _parse_references({}) == []
    assert _parse_references({"choices": [{"message": {"content": "hi"}}]}) == []


def test_parse_product_cards_empty():
    assert _parse_product_cards({"choices": [{"message": {"content": "x"}}]}) == []


def test_is_retryable_skips_4xx_but_retries_429():
    import httpx

    req = httpx.Request("POST", "https://x")
    err4 = httpx.HTTPStatusError("c", request=req, response=httpx.Response(404, request=req))
    err5 = httpx.HTTPStatusError("c", request=req, response=httpx.Response(503, request=req))
    err429 = httpx.HTTPStatusError("c", request=req, response=httpx.Response(429, request=req))
    assert _is_retryable(err4) is False  # 普通 4xx 不重试
    assert _is_retryable(err5) is True  # 5xx 重试
    assert _is_retryable(err429) is True  # 429 限流 → 退避后重试（实战 Phase 6 撞到）
    assert _is_retryable(httpx.ConnectError("x")) is True  # 传输错误重试
