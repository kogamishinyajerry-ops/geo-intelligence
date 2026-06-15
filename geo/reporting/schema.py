"""Schema 生成 CLI：草稿 → 详情页 Article + 列表页 ItemList + 首页 Schema。

    GEO_CATEGORY=tourism python -m geo.reporting.schema [--out DIR] [--validate-only]

零网络 / 零编造 / 确定性：每篇 `content/drafts/*.md` 经纯函数（schema_ld）转成可粘贴的
JSON-LD；我方信息（品牌/作者/logo/域名）走 `GEO_PUBLISHER_*` 注入，缺则 `[待补·HITL]` 占位。
课程四红线由 `validate_jsonld()` 在生成时同步校验并打印。
"""
from __future__ import annotations

import argparse
from pathlib import Path

from geo.category import active_profile
from geo.reporting import schema_ld as S


def _drafts(prof) -> list[Path]:
    d = prof.root / "content" / "drafts"
    return sorted(d.glob("*.md")) if d.exists() else []


def main(argv: list[str] | None = None) -> int:
    prof = active_profile()
    default_out = prof.root / "content" / "schema"

    ap = argparse.ArgumentParser(description="GEO 确定性 JSON-LD/Schema 生成器")
    ap.add_argument("--out", type=Path, default=default_out, help="输出目录")
    ap.add_argument("--validate-only", action="store_true", help="只校验不写文件")
    ap.add_argument("--list-name", default=None, help="列表页 ItemList 的 name（默认按品类）")
    args = ap.parse_args(argv)

    pub = S.PublisherConfig.from_env()
    draft_paths = _drafts(prof)
    if not draft_paths:
        print(f"⚠️ 未找到草稿：{prof.root / 'content' / 'drafts'}")
        return 1

    metas = [S.parse_draft(p) for p in draft_paths]
    list_name = args.list_name or f"{prof.key} · 已审内容合集"

    # 构造全部 schema
    artifacts: list[tuple[str, dict, str | None]] = []  # (filename, obj, comment)
    for m in metas:
        artifacts.append((f"{m.slug}.article.jsonld", S.build_article(m, pub), S.article_comment(m)))
    artifacts.append((
        f"{prof.key}-listing.itemlist.jsonld",
        S.build_itemlist(metas, pub, name=list_name),
        "列表/栏目页 ItemList · 批量收录加速。url 填该栏目页真实地址；numberOfItems 已按草稿数。",
    ))
    artifacts.append((
        "homepage.website-organization.jsonld",
        S.build_homepage(pub),
        "首页 WebSite+Organization 2合1·权威确权。放 <head> 内越靠前越好；sameAs 填真实官方账号。",
    ))

    out_dir = Path(args.out)
    if not args.validate_only:
        out_dir.mkdir(parents=True, exist_ok=True)

    n_block = n_warn = 0
    for fname, obj, comment in artifacts:
        issues = S.validate_jsonld(obj)
        n_block += sum(1 for i in issues if i.startswith("❌"))
        n_warn += sum(1 for i in issues if i.startswith("⚠️"))
        status = "❌" if any(i.startswith("❌") for i in issues) else ("⚠️" if issues else "✅")
        print(f"{status} {fname}")
        for i in issues:
            print(f"     {i}")
        if not args.validate_only:
            # newline="\n" 固定换行，保证跨 OS 字节级可复现（不被平台 CRLF 转换）
            (out_dir / fname).write_text(
                S.render_script(obj, comment=comment), encoding="utf-8", newline="\n")

    # 诚实边界提示：建议平台多为第三方 ⇒ schema 仅对自有落地页有效
    all_platforms = sorted({p for m in metas for p in m.platforms})
    self_owned = pub.has_real_site
    print()
    print(f"品类={prof.key} · 草稿 {len(metas)} 篇 · 阻断 ❌{n_block} · 提示 ⚠️{n_warn}")
    if all_platforms:
        print(f"草稿建议平台：{' / '.join(all_platforms)}")
    if not self_owned:
        print("⚠️ 未配置自有站点（GEO_PUBLISHER_BASE_URL）：Schema 仅对**自有站点/落地页**有效；"
              "发到小红书/知乎/携程等第三方平台无法注入本段。")
    if not args.validate_only:
        print(f"已写入 → {out_dir}（gitignore build 产物，可随草稿更新重新生成）")
    # 有阻断红线问题则非零退出（fail-closed，便于 CI/人审拦截）
    return 1 if n_block else 0


if __name__ == "__main__":
    raise SystemExit(main())
