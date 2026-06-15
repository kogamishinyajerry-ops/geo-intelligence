"""Phase 2 选品：GEO 可赢度评分 + 攻击短名单。

只评 GEO **可测**维度（基于真实证据）：
  - 是否可内容影响（豆包是否联网取货）
  - 竞争缺口（incumbent 权威越低越好打）
  - 品牌空位（豆包是否已点名品牌）
适配 / 供应链 / 毛利 = 人工补（HITL，红线：花钱前人审），本模块不臆造。
每条带证据 ID，可回溯。
"""
from __future__ import annotations

from geo.evidence.schema import BuyerSegment
from geo.reporting.aggregate import load_captures, per_query_rows


def winnability(row: dict) -> dict:
    """GEO 可赢度评分（0-100）+ go/no-go + 理由。透明加权。"""
    if row["n_citations"] == 0:
        return {
            "score": 20.0,
            "go": "观望",
            "reason": "豆包对该 query 不联网/从记忆答 → 内容 GEO 杠杆低；宜改走货架直答/品牌词",
        }
    avg_auth = row["avg_auth"] if row["avg_auth"] is not None else 0.5
    brand_gap = 1.0 if not row["named_brands"] else 0.4
    beat = 1 - avg_auth  # incumbent 权威越低越好打
    score = round(100 * (0.5 * beat + 0.3 * brand_gap + 0.2), 1)
    go = "GO" if score >= 55 else ("候选" if score >= 45 else "观望")
    top = row["top_site"] or row["top_domain"] or "—"
    reason = (
        f"incumbent auth {avg_auth}（{'低·好打' if avg_auth <= 0.45 else '中'}）"
        f"；{'品牌空位' if not row['named_brands'] else '已有品牌 ' + '、'.join(row['named_brands'])}"
        f"；头部 {top}"
    )
    return {"score": score, "go": go, "reason": reason}


def shortlist() -> list[dict]:
    rows = per_query_rows(load_captures(BuyerSegment.A))
    out = [{**r, **winnability(r)} for r in rows]
    out.sort(key=lambda r: r["score"], reverse=True)
    return out


if __name__ == "__main__":
    print(f"{'分':>5}  {'判定':<5}{'主题':<12}{'query'}")
    for r in shortlist():
        print(f"{r['score']:>5}  {r['go']:<5}[{r['theme']:<10}] {r['query']}")
        print(f"        {r['reason']}")
        print(f"        证据 {r['capture_ids'][0]}")
