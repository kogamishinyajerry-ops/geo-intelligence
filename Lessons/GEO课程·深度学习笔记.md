# GEO 生成引擎优化课程 · 深度学习笔记（JSON-LD / Schema 部署）

> **来源**：`Lessons/` 下 4 段录屏教学视频（共 ~23 分钟），内容选自《GEO实战密码》在线版，作者频道「星阅实验室」。演示真实站点：九章格物 `ninegrids.net`、营销云 `semcloud.cn`。
> **本笔记如何生成**：视频按每 8 秒抽帧 → 逐帧重建飞书课程文档正文 + 屏幕代码 + 老师口播字幕；3 段关键代码（首页/列表页/详情页）已对照原始帧逐字符核验，可回溯到具体帧文件（`_extract/frames/lessonN/f_xxx.jpg`）。
> **一句话**：这套课教的是 GEO 的「**部署端 / 供给侧**」——怎么给网站埋结构化数据（JSON-LD），让豆包 / DeepSeek / Kimi / ChatGPT 这些 AI 大模型更高效地**抓取、识别、并把你的内容当成"标准答案"引用推荐**。

---

## 0. 课程地图（4 节讲了什么）

| 节 | 标题 | 类型 | 核心产出 |
|---|---|---|---|
| 第1节 | 网站**首页**怎么部署 JSON-LD/Schema | 概念 + 代码 | 首页 `WebSite + Organization` 双标准模板（2合1·权威确权） |
| 第2节 | 网站**栏目/列表页**怎么部署 Schema（JSON 精讲） | 代码精讲 | 列表页 `ItemList` 目录索引模板 |
| 第3节 | 网站**详情页**部署 Schema/JSON-LD | 代码 + 速查表 | 详情页 `Article` 内容实体模板 + 常用标记类型参考表 |
| 第4节 | 为什么 AI 喜欢把"垃圾文章"当标准答案推荐 | **认知/避坑** | 4 个致命误区（部署的"红线规则"） |

> 第1–3 节是「怎么做」（HOW，给模板），第4节是「别做错」（DON'T，给纪律）。**第4节其实是统御前三节的总纲**——它决定了前面的代码怎么用才不翻车。

---

## 1. 核心概念：JSON-LD 与 Schema 标记是什么、为什么要做

- **JSON-LD** = 一种结构化数据格式（`<script type="application/ld+json">` 包裹的 JSON）。
- **Schema 标记** = 基于 `schema.org` 规范的"内容身份标注规则"。
- **两者结合的作用**：给网页内容加一层 **"AI 可读说明"**，让 AI 精准识别核心信息（我是谁 / 我有什么 / 这篇讲什么），**避免因 HTML 格式混乱而被丢失或答错**。

**为什么对 GEO 重要**（老师反复强调）：AI 大模型抓取网页时，结构化数据让它"读得更快、认得更准"，从而更可能把你的内容**纳入候选、并作为答案引用**。

### 使用四步法（老师给的标准流程）
1. **定标记类型**：按页面功能选 —— 产品页 `Product`、文章/新闻页 `Article`、服务页 `Service`、列表页 `ItemList`、首页 `WebSite`+`Organization`。
2. **梳理核心字段**：先想清楚这个类型必须包含哪些字段（如 `Product` 要产品名/型号/售价/品牌）。
3. **编写 JSON-LD**：统一按 `@context`（语义标准）+ `@type`（标记类型）+ 核心字段 的骨架写，字段格式统一。
4. **嵌入页面**：放进 `<head>` 内（**首选**，不影响展示），也可放 `</body>` 闭合前。
5. **校验有效性**：用谷歌官方校验工具或第三方工具检测，**确保无格式报错**才上线。

---

## 2. 三页面部署范例（指导思想 + 对比表）

**指导思想（一句口诀）**：
> 首页**确权认品牌资质**，列表**归类做索引排序**，详情**实体摘答案**。
> 类型不乱套、字段不造假、校验无报错、AI 优先抓。

### 三页面 Schema 对比表（载重）

| 对比维度 | 首页 Schema | 列表/栏目 Schema | 详情页 Schema |
|---|---|---|---|
| **标准类型** | `WebSite` + `Organization` | `ItemList` | `Article` |
| **核心目的** | 告诉 AI「我是谁、我正规」（确权） | 告诉 AI「我有几个内容、什么顺序」 | 告诉 AI「这篇讲什么」→ 能直接答用户 |
| **必填关键字段** | 域名、品牌、Logo、电话 | 列表总数、条目排序 URL | 标题、摘要、发布时间、作者 |
| **致命禁忌** | 乱填第三方无关链接 | 加 `Article` 字段、乱填假数量 | 摘要过长、日期格式错误 |
| **GEO 流量贡献** | **地基权重**（不直接引流） | **批量收录加速** | **~60% 的直接答案引用流量** ⭐ |

> 🔑 关键认知：**详情页（Article）是直接吃答案流量的主战场（~60%）**——首页和列表页是"打地基 + 加速收录"，真正被 AI 摘成答案引用的是详情页。资源有限时，**详情页 Article 优先做**。

---

## 3. 三套可直接复制的代码模板（已逐字核验）

> 模板文件同时存于 `Lessons/templates/`，可直接取用。下面是带注释的讲解版。

### 3.1 首页：`WebSite + Organization` 双标准（2合1 · 权威确权）

> 同时定义"官网入口 + 企业主体信用"，提升 AI 信任评级、优先入库。用 `@graph` 数组在一段代码里声明两个实体。

```html
<!-- 首页：WebSite + Organization 双标准 Schema -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",                         // 固定：结构化数据标准来源
  "@graph": [                                               // 包含两个实体：网站 + 公司
    {
      "@type": "WebSite",                                   // 第一个：声明这是一个网站
      "name": "你的品牌名称",                                // 网站/品牌名字
      "url": "https://www.your-domain.com"                  // 网站首页地址
    },
    {
      "@type": "Organization",                              // 第二个：声明这是一个公司/机构（确权）
      "name": "你的公司名称",                                // 公司官方全称
      "url": "https://www.your-domain.com",                 // 官网地址
      "logo": "https://www.your-domain.com/images/logo.png",// 公司 logo
      "contactPoint": {                                     // 官方联系方式
        "@type": "ContactPoint",
        "telephone": "400-xxxx-xxx",                        // 客服电话
        "contactType": "customer service"                   // 联系类型：客服
      },
      "sameAs": [                                           // 公司官方社交账号（可选填）
        "https://zhihu.com/xxx",
        "https://weibo.com/xxx"
      ]
    }
  ]
}
</script>
```

**老师现场用真实站点替换占位值的示范**（说明怎么填真值）：
```jsonc
"@type": "WebSite",
"name": "九章格物",
"url": "http://www.ninegrids.net/",
// Organization:
"name": "九章格物(北京)科技有限公司",
"url": "http://www.ninegrids.net/",
"logo": "http://www.ninegrids.net/logo2.png"
```
> 要点：`sameAs` 填**真实的官方知乎/微博等账号**才有确权意义；乱填第三方无关链接是致命禁忌。

### 3.2 列表/栏目页：`ItemList` 目录索引

> 告诉 AI「这是系统化知识库合集」，让它优先**批量抓取整站文章、加速收录**。

```html
<!-- 列表页：ItemList 标准 Schema -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",                         // 固定：结构化数据标准来源
  "@type": "ItemList",                                      // 声明类型：项目列表（栏目/文章/产品列表）
  "name": "栏目页面标题",                                    // 列表页标题（如：新闻中心、产品列表）
  "url": "https://www.your-domain.com/category",            // 当前列表页自身网址
  "numberOfItems": 10,                                      // 该列表下包含的总项目数量（按真实条数填）
  "itemListElement": [                                      // 列表具体内容数组
    {
      "@type": "ListItem",                                  // 类型：列表项
      "position": 1,                                        // 排序位置：第1位
      "url": "https://www.your-domain.com/article-1.html"   // 第1个内容的链接
    },
    {
      "@type": "ListItem",
      "position": 2,
      "url": "https://www.your-domain.com/article-2.html"   // 第2个内容的链接
    },
    {
      "@type": "ListItem",
      "position": 3,
      "url": "https://www.your-domain.com/article-3.html"   // 第3个内容的链接
    }
  ]
}
</script>
```

**JSON 精讲（第2节重点）**：
- `@type: ItemList` 声明"这是一个列表"。
- `numberOfItems` = 列表真实条数（**别乱填假数量**）。
- `itemListElement` 是数组，每个 `{}` 块 = 一条内容，含 `@type: ListItem` / `position`（第几位）/ `url`（该条链接）。
- ⚠️ **最容易踩的坑**：块与块之间**必须有逗号分隔**（JSON 语法，漏一个逗号整段 Schema 失效）。
- 部署位置：放 `<head>` 内，**越靠前越好**。

### 3.3 详情页：`Article` 内容实体（吃答案流量的主战场）

> AI 直接从这里提取标题、摘要当答案，优先引用排名。**详情页 = 告诉 AI"这篇内容的实体是什么"**。

```html
<!-- 详情页：Article 标准 Schema -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",                         // 固定：结构化数据标准来源
  "@type": "Article",                                       // 声明类型：文章（详情页专用）
  "headline": "文章标题",                                    // 文章主标题（≈ 网站 TDK 的 "T")
  "description": "文章简短摘要（120-150字）",                 // 摘要，用于搜索/答案展示
  "author": {                                               // 文章作者信息
    "@type": "Person",                                      // 作者类型：个人
    "name": "作者名称"
  },
  "publisher": {                                            // 发布者（网站/公司）信息
    "@type": "Organization",                                // 发布者类型：机构/公司
    "name": "你的品牌名称",
    "logo": {                                               // 发布者 Logo
      "@type": "ImageObject",
      "url": "https://www.your-domain.com/images/logo.png"
    }
  },
  "datePublished": "2026-01-01",                            // 首次发布时间（ISO 格式 YYYY-MM-DD）
  "dateModified": "2026-01-02",                             // 最后修改时间
  "mainEntityOfPage": "https://www.your-domain.com/article.html"  // 当前文章的绝对地址（完整 URL）
}
</script>
```

**逐字段要点（第3节重点）**：
- `headline` = 文章主标题，相当于 TDK 的 **T**（Title）。
- `description` = 摘要，**≤150 字**（超了 AI 会截断、丢失摘要权重）；AI 时代只要主题写清楚明确即可，它会被当成答案摘要展示。
- `publisher` + `logo`（ImageObject）= **为什么内容被 AI 当答案时会带出你的品牌名 + 网站小图标**，就是在这里配置的。
- `datePublished` / `dateModified` = **必须 ISO 格式 `YYYY-MM-DD`**；内容迭代要更新 `dateModified`。
- `mainEntityOfPage` = 当前文章的**绝对完整 URL**（不是相对路径）。
- **原创文章选 `Article`，日常随笔选 `BlogPosting`，不可混用。**

**部署注意事项（第3节收尾）**：
1. 代码统一放页面底部 `</body>` 之前（也可 `<head>`，老师此处推荐底部）。
2. 只改 域名/名称/logo/电话/链接，**严禁乱删字段**。
3. 日期必须 ISO 格式。
4. 写完用谷歌官方或第三方校验工具一键检测无报错再上线。放置步骤与首页、列表页一模一样。

---

## 4. JSON-LD / Schema 常用标记类型参考表（第3节·速查）

> 不同页面/内容选不同类型，关键属性也不同。已核验的两类如下，其余类目老师列了名（可按需查 schema.org）。

**📌 网站基础信息类**

| 标记类型 | 主要用途 | 关键属性示例 |
|---|---|---|
| `Organization` | 公司/组织基本信息 | `name` `logo` `url` `sameAs`（社媒链接） |
| `WebSite` | 网站整体信息 | `name` `url` `potentialAction`（搜索框动作） |
| `WebPage` | 通用网页信息 | `name` `description` `datePublished` `primaryImageOfPage` |

**📌 内容与文章类**

| 标记类型 | 主要用途 | 关键属性示例 |
|---|---|---|
| `Article` | 文章/资讯 | `headline` `author` `datePublished` `image` |
| `BlogPosting` | 博客文章 | `headline` `author` `datePublished` `articleBody` |
| `NewsArticle` | 新闻 | （新闻类，带发布机构/时间） |
| `Person` | 作者/人物 | `name`（作者实体） |

> 其余类目（老师只列名）：**商业与电子商务类 / 活动与人员类 / 创意作品类 / 教育与就业类 / 健康医疗类**——做对应行业内容时去 schema.org 查具体字段。

---

## 5. 第4节 · 四大致命误区（部署红线规则 — 最重要）⭐

> 现象引入：**你认真写的原创不收录、不推荐；别人东拼西凑的反而收录好、经常被推荐。99% 的人踩这个坑。** 下面拆穿背后真相。

### 误区① "原创就会有流量" —— ❌ 错
- **真相**：**AI 模型识别不了"原创"**，所以也不偏爱原创。
- **模型真正看重的是内容的「结构化」**，不是你有没有原创情怀。
- 👉 行动：摒弃"原创就有流量"思维，把精力放到**结构化（Schema + 内容骨架）**上。

### 误区② "多加 Schema 标记 = 增权重" —— ❌ 错
- **真相**：一个页面加多个 Schema **不会增权重，反而会权重清空**。
- 多个 Schema 互相**冲突、稀释** → 页面失去被抓取的价值 → 失去被推荐机会。
- ✅ 正解：**单页面单个 Schema 标记**。把这一个 Schema 当成"用户提问的标准答案"来输出。

### 误区③ "Schema 一次部署、终生有效" —— ❌ 错
- **真相**：这是懒惰思维，忽略了**内容时效性**。
- 内容过时 → 不满足用户需求 → 模型还在推 → 用户不满 → 跳去竞争对手。
- ✅ 铁律：**Schema 标记必须与页面内容 100% 对应一致**。内容变了而 Schema 没同步 = **被判定作弊** → **信源等级被降低**。
- 👉 行动：时效性内容要持续更新，且**内容一改、Schema 同步改**。

### 误区④ "在 Schema 里塞广告推广信息" —— ❌ 万万不可
- **真相**：Schema 的重点是让模型更快发现**好内容**，不是爬你塞的广告。
- 在 Schema 里加广告 = **自寻死路**，触发平台**风控机制** → **永久降低信源等级**。
- 👉 行动：Schema 只放真实的内容元数据，**绝不夹带广告/推广**。

> 配套书：《GEO实战密码——让你的内容成为 AI 优先推荐的标准答案》。

---

## 6. 落到本项目（geo-intelligence）：两端如何咬合 🔗

**关键定位**：本仓是 GEO 的「**测量端 / 需求侧**」，这套课是「**部署端 / 供给侧**」——正是项目 README 里写的闭环「测量 AI 可见度 → 找空位 → **产真权威内容 → 发布** → 再测量」中，**"发布/部署"那一环的技术细节**（项目目前点了名但没实现）。

```
项目现状（已有）                          课程补的那一环（缺口）
─────────────────────                    ─────────────────────
recon 抓真实 AI 回答  ──┐
metrics 算占答率/空位   │  找到"礼盒按国家送礼整片品牌空位"
content/drafts 产权威稿 ─┘  写好了 gift 10 / tourism 4 篇  ──►  【部署】给草稿网页埋:
                                                                 · 首页 WebSite+Organization（确权）
                                                                 · 列表页 ItemList（让 AI 批量收录这批稿）
                                                                 · 每篇详情页 Article（吃 ~60% 答案引用流量）
                                          再测量 ◄── 发布后回到 recon 复测占答率是否上升
```

### 课程→项目的 5 条直接结论
1. **项目的红线被课程独立印证**：README「❌ 不注入广告、不铺假软文/刷量（会被降权+违规）」≈ 误区①+④；这不是洁癖，是会触发风控**永久降信源等级**的技术事实。
2. **内容已就位，差"结构化部署"临门一脚**：`categories/*/content/drafts/` 里的稿子要真被 AI 摘成答案，**必须**在发布页面埋 `Article` schema（详情页是 60% 流量主战场）。
3. **"单页面单个 Schema"** + **"Schema 与内容 100% 一致"**（误区②③）应成为项目**发布阶段的硬约束**——和项目已有的"确定性/可复现"红线同源。
4. **可量化闭环正好闭合**：部署 Article 后，用项目现成的 recon→metrics 复测占答率/首选率，验证 Schema 是否真带来引用提升（符合项目"证据优先、再测量"）。
5. **可选增强**：项目可加一个 `geo/reporting/` 下的 **schema 生成器**——读 `content/drafts/*.md` 的 front-matter（标题/query/证据ID/发布日期），**确定性**吐出可粘贴的 `Article` JSON-LD（不写死、不用 LLM，与项目"纯函数+确定性抽取"一致）。已先做一个手工样例见 `templates/EXAMPLE_tourism_offbeat_guide.article.jsonld`。

> ⚠️ 诚实边界：课程演示站是企业自有网站（`<head>` 可改）。本项目的内容若发布在小红书/知乎/携程等**第三方平台**，**无法注入自定义 JSON-LD**——Schema 部署只对**自有站点/落地页**有效。第三方平台上，课程的精神层（结构化排版、要点先行、时效更新、单主题）仍适用，但 `<script ld+json>` 那层用不上。这点 README 已隐含（建议平台是小红书/知乎），部署 Schema 主要服务于**自建落地页**场景。

---

## 7. 一页速查（贴墙版）

- **三页面**：首页 `WebSite+Organization`（确权）｜列表页 `ItemList`（收录加速）｜详情页 `Article`（吃答案，~60%）。
- **放哪**：`<head>` 内优先（详情页老师也认可 `</body>` 前）；越靠前越好；写完**必校验**。
- **骨架**：`@context`(schema.org) → `@type` → 核心字段。
- **JSON 坑**：数组项之间**别漏逗号**；日期 **ISO `YYYY-MM-DD`**；`description ≤150 字`；URL 用**绝对地址**。
- **四红线**：① 别迷信原创（模型只认结构化）② **一页一个 Schema**（多了权重清空）③ Schema 必须**随内容更新**（不一致=作弊降权）④ **绝不塞广告**（触发风控永久降级）。
- **类型选择**：原创文 `Article` / 随笔 `BlogPosting` / 产品 `Product` / 服务 `Service`，**不混用**。
```
