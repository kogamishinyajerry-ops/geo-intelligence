"""确定性 JSON-LD/Schema 生成器契约测试（schema_ld）。

红线守护：
- **确定性/可复现**：build_article(parse_draft(x)) 两次 render → 完全相同的字节。
- **证据优先/不编造**：我方信息缺失时为 [待补·HITL]，证据 ID 进注释不进 schema 字段。
- **课程四红线写成校验**：单页面单 Schema、description≤150、ISO 日期、不得含广告。

本文件按 active profile（conftest 设 GEO_CATEGORY）跑该品类真实草稿 + 合成用例验校验器。
"""
from __future__ import annotations

import json

import pytest

from geo.category import active_profile
from geo.reporting import schema_ld as S


def _draft_paths():
    d = active_profile().root / "content" / "drafts"
    return sorted(d.glob("*.md"))


def _metas():
    return [S.parse_draft(p) for p in _draft_paths()]


# ── 真实草稿：解析 / 确定性 / 校验 ──────────────────────────────────────────
def test_drafts_exist():
    assert _draft_paths(), "该品类应有内容草稿"


@pytest.mark.parametrize("path", _draft_paths(), ids=lambda p: p.stem)
def test_parse_real_draft(path):
    m = S.parse_draft(path)
    assert m.headline, "headline 不应为空（取自 H1）"
    assert m.description, "description 不应为空（取自一句话框架）"
    assert len(m.description) <= S.MAX_DESCRIPTION, "description 必须 ≤150（课程红线）"
    assert m.queries, "目标 query 不应为空"
    # 抽到的 capture_id 必须长得像真证据 ID（可回溯，红线§1）
    for cid in m.capture_ids:
        assert "-" in cid and cid.split("-")[0].isalpha()


def test_build_is_byte_deterministic():
    """同输入两次构造 → 完全相同字节（byte-reproducibility 红线）。"""
    pub = S.PublisherConfig()
    for m in _metas():
        a = S.render_script(S.build_article(m, pub), comment=S.article_comment(m))
        b = S.render_script(S.build_article(m, pub), comment=S.article_comment(m))
        assert a == b


def test_real_articles_have_no_blocking_issues():
    """真实草稿生成的 Article 不应触发任何 ❌（占位 ⚠️ 允许）。"""
    pub = S.PublisherConfig()
    for m in _metas():
        issues = S.validate_jsonld(S.build_article(m, pub))
        blocking = [i for i in issues if i.startswith("❌")]
        assert not blocking, f"{m.slug}: {blocking}"


def test_real_articles_parse_as_json():
    pub = S.PublisherConfig()
    for m in _metas():
        obj = S.build_article(m, pub)
        assert json.loads(S.to_json(obj))["@type"] == "Article"


def test_keywords_are_the_real_queries():
    pub = S.PublisherConfig()
    m = _metas()[0]
    assert S.build_article(m, pub)["keywords"] == list(m.queries)


def test_itemlist_count_matches_drafts():
    metas = _metas()
    il = S.build_itemlist(metas, S.PublisherConfig(), name="x")
    assert il["numberOfItems"] == len(metas)
    assert len(il["itemListElement"]) == len(metas)
    assert [e["position"] for e in il["itemListElement"]] == list(range(1, len(metas) + 1))


def test_homepage_graph_is_website_plus_organization():
    hp = S.build_homepage(S.PublisherConfig())
    types = sorted(n["@type"] for n in hp["@graph"])
    assert types == ["Organization", "WebSite"]
    # 占位首页仅应有 ⚠️（待补），不应有 ❌ 阻断
    assert not [i for i in S.validate_jsonld(hp) if i.startswith("❌")]


# ── 校验器：课程四红线（合成输入） ─────────────────────────────────────────
def _fake_meta(**kw):
    base = dict(
        slug="t", headline="标题", description="摘要", queries=("q",),
        capture_ids=(), recon_date="2026-01-01", platforms=(), status=None,
        source_path="t.md",
    )
    base.update(kw)
    return S.DraftMeta(**base)


def test_redline_no_ads_in_schema():
    """红线④：schema 内含广告/推广词 → ❌。"""
    m = _fake_meta(description="本店限时优惠，扫码加微信立即购买")
    issues = S.validate_jsonld(S.build_article(m, S.PublisherConfig()))
    assert any(i.startswith("❌") and "广告" in i for i in issues)


def test_redline_single_schema_only():
    """红线②：非首页的 @graph 多实体 → ❌；合法首页 @graph 不报 ❌。"""
    bad = {"@graph": [{"@type": "Article"}, {"@type": "Article"}]}
    assert any(i.startswith("❌") for i in S.validate_jsonld(bad))
    good = S.build_homepage(S.PublisherConfig(
        brand="b", company="c", base_url="https://x.com", logo_url="https://x.com/l.png"))
    assert not [i for i in S.validate_jsonld(good) if i.startswith("❌")]


def test_description_over_150_blocks():
    long = {"@context": "https://schema.org", "@type": "Article", "description": "字" * 151}
    assert any("description" in i and i.startswith("❌") for i in S.validate_jsonld(long))


@pytest.mark.parametrize("bad_date", ["2026/1/1", "2026-13-40", "2026-02-30", "2026-1-1", "26-01-01"])
def test_non_iso_or_impossible_date_blocks(bad_date):
    """形状错 + 形状对但日历非法（2026-13-40 / 2026-02-30）都要被挡。"""
    bad = {"@context": "https://schema.org", "@type": "Article", "headline": "h",
           "description": "x", "datePublished": bad_date}
    assert any("datePublished" in i and i.startswith("❌") for i in S.validate_jsonld(bad))


def test_type_as_array_blocks():
    """红线②绕过：@type 写成数组（多类型）→ ❌。"""
    bad = {"@context": "https://schema.org", "@type": ["Article", "FAQPage"],
           "headline": "h", "description": "x"}
    assert any("@type" in i and i.startswith("❌") for i in S.validate_jsonld(bad))


def test_graph_with_top_level_type_blocks():
    """@graph 同时带顶层 @type → ❌。"""
    bad = {"@context": "https://schema.org", "@type": "Article",
           "@graph": [{"@type": "WebSite"}, {"@type": "Organization"}]}
    assert any(i.startswith("❌") for i in S.validate_jsonld(bad))


def test_graph_extra_node_blocks():
    """@graph 混入第三个/无类型节点 → ❌（只允许 WebSite+Organization 恰两节点）。"""
    bad = {"@graph": [{"@type": "WebSite"}, {"@type": "Organization"}, {"@type": "Article"}]}
    assert any(i.startswith("❌") for i in S.validate_jsonld(bad))


def test_empty_headline_article_blocks():
    bad = {"@context": "https://schema.org", "@type": "Article", "headline": "  ", "description": "x"}
    assert any("headline" in i and i.startswith("❌") for i in S.validate_jsonld(bad))


@pytest.mark.parametrize("ad", ["立即 购买", "ＢＵＹ　ＮＯＷ", "Buy Now", "限　时优惠"])
def test_ad_term_variants_blocked(ad):
    """广告词的夹空格/全角/大小写/英文变体都要被归一化匹配挡住。"""
    bad = {"@context": "https://schema.org", "@type": "Article", "headline": "h", "description": ad}
    assert any(i.startswith("❌") and "广告" in i for i in S.validate_jsonld(bad))


def test_httpx_url_warns():
    """httpx:// 这类伪 scheme 不应被当作合法绝对 URL。"""
    bad = {"@context": "https://schema.org", "@type": "Article", "headline": "h",
           "description": "x", "mainEntityOfPage": "httpx://evil"}
    assert any("mainEntityOfPage" in i for i in S.validate_jsonld(bad))


def test_clean_description_truncates_at_sentence_boundary():
    text = "第一句结束。" + "第二句很长" * 40
    out = S.clean_description(text)
    assert len(out) <= S.MAX_DESCRIPTION
    assert out.endswith("。") or len(out) == S.MAX_DESCRIPTION


def test_placeholder_publisher_warns_for_hitl():
    issues = S.validate_jsonld(S.build_article(_fake_meta(), S.PublisherConfig()))
    assert any("待补" in i and i.startswith("⚠️") for i in issues)


def test_publisher_from_env_resolves_placeholders():
    env = {
        "GEO_PUBLISHER_BRAND": "牌", "GEO_PUBLISHER_COMPANY": "公司",
        "GEO_PUBLISHER_BASE_URL": "https://x.com", "GEO_PUBLISHER_LOGO": "https://x.com/l.png",
        "GEO_PUBLISHER_AUTHOR": "作者", "GEO_PUBLISHER_SAMEAS": "https://a.com, https://b.com",
        "GEO_PUBLISHER_DATE": "2026-06-16",
    }
    pub = S.PublisherConfig.from_env(env)
    assert pub.has_real_site and pub.same_as == ("https://a.com", "https://b.com")
    art = S.build_article(_fake_meta(recon_date=None), pub)
    assert art["mainEntityOfPage"].startswith("https://x.com/")
    assert art["datePublished"] == "2026-06-16"  # recon_date 缺 → 回退 default_date
    assert not [i for i in S.validate_jsonld(art) if i.startswith("❌") or "待补" in i]
