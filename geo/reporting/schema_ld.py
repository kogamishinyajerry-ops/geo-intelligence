"""确定性 JSON-LD / Schema 生成器（GEO 部署端）。

把已审的内容草稿（`categories/<cat>/content/drafts/*.md`）确定性地转成可粘贴的
结构化数据：详情页 `Article`、列表页 `ItemList`、首页 `WebSite+Organization`。
课程萃取的 canon 见 `Lessons/GEO课程·深度学习笔记.md`；本模块把其中**四条红线**
写成 `validate_jsonld()` 的可执行校验，而非纸面规则。

红线对齐（与 `~/CLAUDE.md` / 项目 CLAUDE.md 同源）：
- **确定性 / 可复现**（红线§1-2）：纯函数，无墙钟、无随机、无 LLM；同输入两次跑出**完全相同的字节**。
  日期来自草稿/配置而非 `now()`，故 JSON-LD 字节级可复现（测试守护）。
- **证据优先 / 不编造**（红线§1）：品牌 / 作者 / logo / 域名等"我方信息"不在草稿里 ⇒ 一律
  `[待补·HITL]` 占位，靠 `PublisherConfig.from_env()` 注入真值；草稿的 `证据 ID` 原样写进
  HTML 注释做可回溯，**绝不**塞进 schema 字段。
- **HITL 闸门**（红线§3）：含 `[待补]` 的产物 `validate_jsonld()` 会发 ⚠️ 提示"发布前需人审填真值"。

课程四红线 → 代码校验（`validate_jsonld`）：
1. 模型只认结构化、不认原创 → 生成器本身就是把内容结构化。
2. **单页面单个 Schema** → `Article`/`ItemList` 顶层只允许一个 `@type`（首页 `WebSite+Organization`
   是课程钦定的 `@graph` 2合1 唯一例外）。
3. **Schema 必须与内容 100% 一致、随内容更新** → headline/description/keywords 全部从草稿抽取，
   `dateModified` 提示同步；不一致=作弊降权。
4. **绝不在 schema 塞广告** → 扫描所有字符串值命中广告词 ⇒ ❌。

另含课程视频没讲、但会让人翻车的正确性校验：description ≤150 字、日期 ISO `YYYY-MM-DD`、
URL 绝对地址、JSON-LD 不允许 `//` 注释（本模块输出本就是合法 JSON）。
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

# ── 常量 ──────────────────────────────────────────────────────────────────
PLACEHOLDER = "[待补·HITL]"          # 我方信息缺失时的统一占位（绝不编造，红线§1）
MAX_DESCRIPTION = 150               # 课程红线：摘要超长会被 AI 截断、丢权重
HEADLINE_SOFT_LIMIT = 110          # Google 富媒体对 headline 的截断经验值（仅 ⚠️）
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ANY_ISO_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_CAPTURE_ID = re.compile(r"`([a-z]+-[A-Za-z]-\d{8}T\d{6}Z-[0-9a-f]+)`")
# 段间分隔符（中文全角竖线 ｜ / 半角 | / 顿号都可能出现在 query 行）
_QUERY_SPLIT = re.compile(r"[｜|]")
_SENTENCE_END = "。！？"           # 主要句界
_SOFT_BREAK = "；，、"             # 次要断点
# 广告/推广词命中即红线④违规（让模型抓好内容，不是爬广告）
_AD_TERMS = (
    "广告", "推广", "促销", "限时", "优惠", "折扣", "特价", "秒杀", "包邮",
    "扫码", "加微信", "加我", "私信", "代理", "加盟", "招商", "联系电话",
    "立即购买", "立即下单", "点击购买", "咨询客服", "抢购", "下单立减",
    # 英文促销词（归一化后匹配，覆盖大小写/全角/夹空格变体）
    "buynow", "limitedtime", "discount", "coupon", "promocode", "flashsale", "onsale",
)


def _norm_text(s: str) -> str:
    """归一化：NFKC（全角→半角）+ casefold（大小写）+ 去所有空白。用于广告词鲁棒匹配。"""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", s).casefold())


_AD_TERMS_NORM = tuple(dict.fromkeys(_norm_text(t) for t in _AD_TERMS))
_URL_KEYS = {"url", "mainEntityOfPage", "logo"}  # 应为绝对 http(s) 地址的字段
_HTTP_SCHEME = re.compile(r"https?://")


# ── 数据模型 ──────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class DraftMeta:
    """从一篇草稿确定性抽取的元数据（纯抽取，不含我方信息）。"""

    slug: str
    headline: str
    description: str
    queries: tuple[str, ...]
    capture_ids: tuple[str, ...]
    recon_date: str | None
    platforms: tuple[str, ...]
    status: str | None
    source_path: str


@dataclass(frozen=True)
class PublisherConfig:
    """我方发布主体信息。默认全是 `[待补·HITL]` 占位；真值靠 env 注入，绝不编造。"""

    brand: str = f"{PLACEHOLDER} 品牌名"
    company: str = f"{PLACEHOLDER} 公司全称"
    base_url: str = ""                      # 自有站点根（空=未配置，URL 走占位）
    logo_url: str = ""
    author: str = f"{PLACEHOLDER} 作者"
    telephone: str = ""
    same_as: tuple[str, ...] = ()
    default_date: str | None = None         # 草稿无日期时的兜底发布日（ISO）

    @classmethod
    def from_env(cls, env: dict | None = None) -> "PublisherConfig":
        """从 `GEO_PUBLISHER_*` 读真值（部署时填，不改代码）。缺失项保持占位。"""
        e = os.environ if env is None else env
        same_as = tuple(
            s.strip() for s in e.get("GEO_PUBLISHER_SAMEAS", "").split(",") if s.strip()
        )
        kw = dict(
            brand=e.get("GEO_PUBLISHER_BRAND"),
            company=e.get("GEO_PUBLISHER_COMPANY"),
            base_url=e.get("GEO_PUBLISHER_BASE_URL"),
            logo_url=e.get("GEO_PUBLISHER_LOGO"),
            author=e.get("GEO_PUBLISHER_AUTHOR"),
            telephone=e.get("GEO_PUBLISHER_TEL"),
            default_date=e.get("GEO_PUBLISHER_DATE"),
        )
        base = cls(same_as=same_as) if same_as else cls()
        # 仅覆盖 env 里真正给了值的字段（None 保留占位默认）
        return replace(base, **{k: v for k, v in kw.items() if v})

    @property
    def has_real_site(self) -> bool:
        """base_url 是否为真实自有站点（决定 URL 走真值还是占位）。"""
        return bool(self.base_url) and "待补" not in self.base_url


# ── 草稿解析（确定性） ──────────────────────────────────────────────────────
def clean_description(text: str, limit: int = MAX_DESCRIPTION) -> str:
    """清洗摘要 + 确定性截断到 ≤limit 字。

    去 markdown 强调（`**` / `「」` / 反引号）、折叠空白；超长则优先在句界（。！？）截，
    其次在次要断点（；，、）截，都没有再硬截。纯函数：同输入→同输出。
    """
    s = text.strip()
    s = s.replace("**", "").replace("「", "").replace("」", "").replace("`", "")
    s = re.sub(r"\s+", "", s)  # 中文正文去掉所有空白，保持紧凑
    if len(s) <= limit:
        return s
    window = s[:limit]
    # 优先句界
    cut = max(window.rfind(c) for c in _SENTENCE_END)
    if cut < limit * 0.5:  # 句界太靠前则退而求次要断点
        soft = max(window.rfind(c) for c in _SOFT_BREAK)
        cut = soft if soft > cut else cut
    if cut <= 0:
        return window  # 无任何断点：硬截
    return s[: cut + 1]


def _extract_description(lines: list[str]) -> str:
    """取 `## 一句话框架` 标题后的第一段为摘要。"""
    for i, ln in enumerate(lines):
        if ln.lstrip("#").strip().startswith("一句话框架"):
            para: list[str] = []
            for nxt in lines[i + 1 :]:
                t = nxt.strip()
                if t.startswith("#"):
                    break
                if not t:
                    if para:  # 段落结束
                        break
                    continue   # 跳过标题与正文间的空行
                para.append(t)
            return clean_description("".join(para))
    return ""


def parse_draft(path: str | Path) -> DraftMeta:
    """把一篇草稿确定性解析为 DraftMeta。不读我方信息、不调 LLM。"""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    lines = text.splitlines()

    headline = ""
    for ln in lines:
        if ln.startswith("# "):
            headline = ln[2:].strip()
            break

    blockquote = "\n".join(ln for ln in lines if ln.lstrip().startswith(">"))

    queries: tuple[str, ...] = ()
    m = re.search(r"目标\s*query[：:]\s*(.+)", blockquote)
    if m:
        # 仅按全角/半角竖线拆（草稿约定）；不拆 / 、——它们出现在单条 query 内部
        raw = _QUERY_SPLIT.split(m.group(1))
        queries = tuple(q.strip() for q in raw if q.strip())

    capture_ids = tuple(dict.fromkeys(_CAPTURE_ID.findall(blockquote)))  # 去重保序

    recon_date = None
    dm = _ANY_ISO_DATE.search(blockquote)
    if dm:
        recon_date = dm.group(1)

    platforms: tuple[str, ...] = ()
    pm = re.search(r"建议平台[：:]\s*([^｜|]+)", blockquote)
    if pm:
        platforms = tuple(x.strip() for x in re.split(r"[/、]", pm.group(1)) if x.strip())

    status = None
    sm = re.search(r"状态[：:]\s*\*{0,2}([^｜|*\n]+)", blockquote)
    if sm:
        status = sm.group(1).strip()

    return DraftMeta(
        slug=p.stem,
        headline=headline,
        description=_extract_description(lines),
        queries=queries,
        capture_ids=capture_ids,
        recon_date=recon_date,
        platforms=platforms,
        status=status,
        source_path=str(p),
    )


# ── Schema 构造（纯函数，返回插入有序 dict） ─────────────────────────────────
def _page_url(pub: PublisherConfig, slug: str) -> str:
    if pub.has_real_site:
        return f"{pub.base_url.rstrip('/')}/{slug}.html"
    return f"[待补·HITL 自有域名]/{slug}.html"


def _publisher_block(pub: PublisherConfig) -> dict:
    logo = pub.logo_url or "[待补·HITL logo 绝对地址]"
    return {
        "@type": "Organization",
        "name": pub.brand,
        "logo": {"@type": "ImageObject", "url": logo},
    }


def build_article(meta: DraftMeta, pub: PublisherConfig) -> dict:
    """详情页 Article。字段全部来自草稿（headline/description/keywords）或我方配置。"""
    art: dict = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": meta.headline,
        "description": meta.description,
    }
    if meta.queries:
        art["keywords"] = list(meta.queries)  # 真实高意图 query = 最强 GEO 关键词信号
    art["author"] = {"@type": "Person", "name": pub.author}
    art["publisher"] = _publisher_block(pub)
    date = meta.recon_date or pub.default_date
    if date:
        art["datePublished"] = date
        art["dateModified"] = date
    art["mainEntityOfPage"] = _page_url(pub, meta.slug)
    return art


def build_itemlist(metas: list[DraftMeta], pub: PublisherConfig, *,
                   name: str, list_slug: str = "index") -> dict:
    """列表/栏目页 ItemList：让 AI 把这批内容当系统化知识库批量收录。"""
    items = []
    for i, m in enumerate(metas, start=1):
        items.append({
            "@type": "ListItem",
            "position": i,
            "url": _page_url(pub, m.slug),
        })
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": name,
        "url": (f"{pub.base_url.rstrip('/')}/{list_slug}.html"
                if pub.has_real_site else f"[待补·HITL 自有域名]/{list_slug}.html"),
        "numberOfItems": len(metas),
        "itemListElement": items,
    }


def build_homepage(pub: PublisherConfig) -> dict:
    """首页 WebSite + Organization（@graph 2合1·权威确权）——课程钦定的唯一多实体例外。"""
    site_url = pub.base_url or "[待补·HITL 自有域名]"
    org: dict = {
        "@type": "Organization",
        "name": pub.company,
        "url": site_url,
        "logo": pub.logo_url or "[待补·HITL logo 绝对地址]",
    }
    if pub.telephone:
        org["contactPoint"] = {
            "@type": "ContactPoint",
            "telephone": pub.telephone,
            "contactType": "customer service",
        }
    if pub.same_as:
        org["sameAs"] = list(pub.same_as)
    return {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "name": pub.brand, "url": site_url},
            org,
        ],
    }


# ── 序列化（确定性） ────────────────────────────────────────────────────────
def to_json(obj: dict) -> str:
    """确定性 JSON 串：保持插入顺序、中文不转义、2 空格缩进、无尾随空白。"""
    return json.dumps(obj, ensure_ascii=False, indent=2)


def render_script(obj: dict, *, comment: str | None = None) -> str:
    """包成可粘贴的 `<script type="application/ld+json">`，可选前置 HTML 注释（在 JSON 体外）。"""
    body = to_json(obj)
    head = f"<!--\n{comment}\n-->\n" if comment else ""
    return f'{head}<script type="application/ld+json">\n{body}\n</script>\n'


def article_comment(meta: DraftMeta) -> str:
    """Article 的 HTML 注释：可回溯证据 ID + 来源草稿（红线§1，证据进注释不进 schema）。"""
    ev = "、".join(meta.capture_ids) if meta.capture_ids else "（该草稿未标证据 ID）"
    return (f"详情页 Article · 源草稿 {Path(meta.source_path).name}\n"
            f"证据可回溯：{ev}\n"
            f"发布前人审：填真值替换所有 [待补·HITL]；确认 datePublished 为实际发布日；"
            f"校验无报错再上线。第三方平台（小红书/知乎等）无法注入本段，仅自有落地页适用。")


# ── 校验器：课程四红线 + 正确性，写成可执行规则 ─────────────────────────────
def _walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_strings(v)


def _iter_kv(obj):
    """递归产出所有 (key, value) 对（dict 嵌套），用于按字段名校验（如 URL 字段）。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k, v
            yield from _iter_kv(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_kv(v)


def validate_jsonld(obj: dict) -> list[str]:
    """对一段 schema dict 跑全部红线 + 正确性校验。

    返回问题列表：`❌` = 阻断（违红线/会校验失败），`⚠️` = 提示（多为 HITL 待补）。
    空列表 = 干净。本函数纯函数、确定性。
    """
    issues: list[str] = []
    raw_type = obj.get("@type")
    top_type = raw_type if isinstance(raw_type, str) else None

    # 红线②：单页面单个 Schema（@graph 仅首页 WebSite+Organization 例外）
    if "@graph" in obj:
        if raw_type is not None:
            issues.append("❌ 含 @graph 时不应再有顶层 @type（单页面单 Schema，红线②）")
        graph_types = [n.get("@type") if isinstance(n, dict) else None
                       for n in obj.get("@graph", [])]
        if sorted(t for t in graph_types if isinstance(t, str)) != ["Organization", "WebSite"]:
            issues.append(f"❌ @graph 仅允许首页 WebSite+Organization 2合1，实得 {graph_types}（红线②：多 Schema 冲突→权重清空）")
    elif raw_type is None:
        issues.append("❌ 缺顶层 @type")
    elif not isinstance(raw_type, str):
        issues.append(f"❌ @type 必须是单个字符串（单页面单 Schema，红线②），实得 {raw_type!r}")

    # Article 必填 headline（缺/空 → 阻断，防静默生成空标题）
    if top_type == "Article":
        head = obj.get("headline")
        if not (isinstance(head, str) and head.strip()):
            issues.append("❌ Article 缺 headline 或为空（必填关键字段）")

    # description ≤150（课程红线：超长被 AI 截断丢权重）
    desc = obj.get("description")
    if isinstance(desc, str) and len(desc) > MAX_DESCRIPTION:
        issues.append(f"❌ description {len(desc)} 字 > {MAX_DESCRIPTION}（会被 AI 截断丢摘要权重）")

    # headline 软上限
    head = obj.get("headline")
    if isinstance(head, str) and len(head) > HEADLINE_SOFT_LIMIT:
        issues.append(f"⚠️ headline {len(head)} 字 > {HEADLINE_SOFT_LIMIT}（Google 富媒体可能截断，建议精简）")

    # 日期：ISO 形状 + 真实可解析（挡 2026-13-40 / 2026-02-30 这类形状对但非法的日期）
    for key in ("datePublished", "dateModified"):
        v = obj.get(key)
        if v is None:
            continue
        s = str(v)
        valid = bool(_ISO_DATE.match(s))
        if valid:
            try:
                date.fromisoformat(s)
            except ValueError:
                valid = False
        if not valid:
            issues.append(f"❌ {key}={v!r} 非合法 ISO YYYY-MM-DD（日期格式错误是致命禁忌）")
    # Article 缺发布时间：课程列为必填关键字段，缺则提示人审补（不编造）
    if top_type == "Article" and "datePublished" not in obj:
        issues.append("⚠️ Article 缺 datePublished（课程必填字段，发布前人审补真实发布日）")

    # URL 字段应为绝对 http(s) 地址（递归查 url/mainEntityOfPage/logo；挡 httpx:// 这类误过）
    for k, v in _iter_kv(obj):
        if k in _URL_KEYS and isinstance(v, str) and "待补" not in v and not _HTTP_SCHEME.match(v):
            issues.append(f"⚠️ {k} 应为绝对 URL（http(s):// 开头），实得 {v!r}")

    # 红线④：schema 内不得含广告/推广词（归一化匹配：NFKC + casefold + 去空白）
    for s in _walk_strings(obj):
        ns = _norm_text(s)
        for term in _AD_TERMS_NORM:
            if term and term in ns:
                issues.append(f"❌ 命中广告/推广词「{term}」：{s[:40]}…（红线④：触发风控→永久降信源等级）")
                break

    # HITL：残留待补占位
    if any("待补" in s for s in _walk_strings(obj)):
        issues.append("⚠️ 含 [待补·HITL] 占位：发布前需人审填真值（红线§3 HITL 闸门）")

    # JSON-LD 合法性（应恒为真，构造保证；防御性自检）
    try:
        json.loads(to_json(obj))
    except Exception as e:  # pragma: no cover
        issues.append(f"❌ 非法 JSON：{e}")

    return issues
