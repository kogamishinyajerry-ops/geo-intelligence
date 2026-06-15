# GEO 课程三页面 JSON-LD 模板（可直接取用）

源自 `../GEO课程·深度学习笔记.md`（《GEO实战密码》课程第1–3节）。

| 文件 | 页面 | 类型 | 作用 |
|---|---|---|---|
| `homepage.website-organization.jsonld` | 首页 | `WebSite`+`Organization` | 权威确权（地基权重） |
| `listpage.itemlist.jsonld` | 列表/栏目页 | `ItemList` | 批量收录加速 |
| `article.detail.jsonld` | 文章详情页 | `Article` | 吃 ~60% 答案引用流量 ⭐ |
| `EXAMPLE_tourism_offbeat_guide.article.jsonld` | 示例 | `Article` | 把项目真实草稿包成 Article 的样例 |

## 用法
1. 复制对应文件的 `<script type="application/ld+json"> … </script>` 整段。
2. 把占位值（域名/品牌/logo/电话/链接/日期）替换为真值。
3. 贴进网页 `<head>` 内（**越靠前越好**；详情页也可放 `</body>` 前）。
4. 上线前用谷歌富媒体结果测试 / schema.org validator 校验**无报错**。

## ⚠️ 关键正确性提醒（课程视频里没说、但会让你翻车的点）
- **JSON-LD 是严格 JSON，不允许 `//` 注释。** 课程视频和本仓笔记里为了讲解写了 `// 注释`，**真正部署前必须删掉所有注释**，否则校验器报错、整段失效。本目录的 `.jsonld` 文件已是**无注释的合法 JSON**（仅最外层 HTML `<!-- -->` 注释，那是 HTML 注释、在 `<script>` 外或会被忽略——粘贴时连同 `<script>` 标签一起放进 HTML 即可，JSON 体内无注释）。
- 数组项之间**别漏逗号**；日期用 ISO `YYYY-MM-DD`；`description ≤150 字`；URL 用**绝对地址**。
- **一页一个 Schema**（多个会冲突、权重清空）。
- Schema 必须与页面内容 **100% 一致**，内容更新时同步改 `dateModified`（不一致=作弊降权）。
- **绝不在 Schema 里塞广告**（触发风控、永久降信源等级）。

## 本项目适用边界
- ✅ 自有站点 / 落地页：可注入，完整适用。
- ❌ 小红书 / 知乎 / 携程等第三方平台：无法注入自定义 `<script ld+json>`；此时只有课程的"结构化排版/要点先行/时效更新/单主题"精神层适用。
