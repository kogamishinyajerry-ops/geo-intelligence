"""把聚合结果转成 Notion create-pages 的 properties 负载（可复用，§4.4 reporting）。

Python 只生成负载；实际推送由编排层（带 Notion MCP）执行。
__main__ 打印 JSON 块，供推送时使用。
"""
from __future__ import annotations

import json

from geo.evidence.schema import BuyerSegment, Capture
from geo.reporting.aggregate import load_captures, per_query_rows

_SEG_LABEL = {"A": "A 中国人送老外", "B": "B 老外自买"}


def opp_properties(row: dict) -> dict:
    top = row["top_site"] or row["top_domain"]
    top_str = f"{top}（覆盖{row['top_coverage']}）" if top else "—（无引用）"
    brands = "、".join(row["named_brands"]) if row["named_brands"] else "无"
    notes = (
        f"品牌:{brands}; 引用{row['n_citations']}条; 头部域名 {row['top_domain'] or '—'}"
        f"({row['top_coverage']}); avg_auth {row['avg_auth']}; 证据 {','.join(row['capture_ids'])}"
    )
    return {
        "Query": row["query"],
        "Segment": _SEG_LABEL.get(row["segment"], "未定"),
        "Intent": "purchase",
        "该走货架 Shelf": row["shelf"] if row["shelf"] in ("抖音商城", "Shopify/独立站") else "未定",
        "空位评分 Opportunity": row["opportunity"],
        "竞争强度 Competition": row["competition"],
        "头部品牌 Top Brand": top_str,
        "证据数 Captures": row["n_captures"],
        "备注 Notes": notes[:1900],
    }


def evid_properties(c: Capture) -> dict:
    brands = "、".join(c.named_brands) if c.named_brands else "—"
    return {
        "Capture ID": c.id,
        "Engine": c.engine if c.engine in ("doubao", "mock-perplexity", "perplexity", "openai") else "doubao",
        "Segment": _SEG_LABEL.get(c.buyer_segment.value, "未定"),
        "Query": c.query,
        "Mock?": "__YES__" if c.is_mock else "__NO__",
        "Named Brands": brands,
        "Cited": len(c.cited_sources),
        "Product Cards": len(c.product_cards),
        "Links": len(c.links),
        "Sentiment": c.sentiment.value,
        "date:Captured:start": c.timestamp.strftime("%Y-%m-%d"),
        "Raw Path": c.raw_capture_path or "",
    }


if __name__ == "__main__":
    caps = load_captures(BuyerSegment.A)
    caps_by_q = {}
    for c in caps:
        caps_by_q.setdefault(c.query, c)  # 1 capture/query in this batch
    rows = per_query_rows(caps)

    opp = [{"properties": opp_properties(r)} for r in rows]
    evid = [{"properties": evid_properties(caps_by_q[r["query"]])} for r in rows]

    print("===OPP_UPDATE===")
    print(json.dumps(opp[0]["properties"], ensure_ascii=False))
    print("===OPP_CREATE_REST===")
    print(json.dumps([p for p in opp[1:]], ensure_ascii=False))
    print("===EVID_UPDATE===")
    print(json.dumps(evid[0]["properties"], ensure_ascii=False))
    print("===EVID_CREATE_REST===")
    print(json.dumps([p for p in evid[1:]], ensure_ascii=False))
