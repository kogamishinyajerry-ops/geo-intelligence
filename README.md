# GEO Intelligence · 可审计的生成式引擎优化工作流

> **一句话**：测量「当用户问 AI（豆包/ChatGPT）某个问题时，AI 推荐了谁、谁是空位」，再针对空位产出真权威内容去占位——全程证据可回溯、可复现、人审后才发布。

**GEO（Generative Engine Optimization，生成式引擎优化）** 是 SEO 的下一代：用户越来越不自己搜索，而是直接问 AI。这套系统把「**测量 AI 可见度 → 找内容空位 → 产真权威内容 → 发布 → 再测量**」这个闭环自动化、可审计化。

本仓 = **一个共享引擎 `geo/` + 两个品类配置 `categories/<cat>/`**，品类靠环境变量 `GEO_CATEGORY` 选；加新品类只需加一个 `categories/<new>/` + 注册 profile，引擎零改动。

| 主题 | 目录 | 在测什么 | 实证数据 |
| --- | --- | --- | --- |
| 🎁 高端商务伴手礼盒 | [`categories/gift_box/`](categories/gift_box/) | 送外国客户的礼盒，豆包推荐哪些品牌、哪些 query 是品牌空位 | 52 条真实证据 · 10 篇内容草稿 |
| 🗺️ 上海文旅景点 | [`categories/tourism/`](categories/tourism/) | 游客问"上海去哪玩"，豆包推荐哪些景点、谁被钉死、哪里是空位 | 92 条真实证据 · 4 篇内容草稿 |

## 这套系统能 / 不能做什么（最重要）

- ✅ 自动化**测量**：抓 AI 引擎的真实回答 → 存档原始证据 → 算占答率/提及率/首选推荐率/空位评分。
- ✅ 找空位、产真权威内容（人审后发布）、再测量，闭环迭代。
- ❌ **不**保证"进答案"，**不**注入广告、**不**铺假软文/刷量（脆弱 + 会被模型降权 + 违规）。

## 核心设计（为什么可信）

- **证据优先，拒绝幻觉**：所有指标从存档的原始 AI 回答（原文 + 时间戳 + 原始响应体）计算，可回溯到证据 ID。不凭模型印象编数字。
- **确定性抽取**：实体（品牌/景点）只匹配白名单 `config/watchlist.yaml`，正则查表、不用 LLM 做 NER → 同输入跑两次结论一致。
- **指标 = 纯函数**：占答率/提及率/首选推荐率/空位评分都是对证据表的纯函数（`geo/metrics/`），禁止旁路。
- **HITL 人审闸门**：花钱前、对外发布前必须人审，系统默认不自动发布。
- **Truth plane = git**：代码、配置、原始证据库、内容草稿全部版本化、可审计、可 diff。

## 怎么跑（一个共享引擎，品类靠 `GEO_CATEGORY` 选）

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"

# 引擎测试（按品类分别跑，env 选品类）
GEO_CATEGORY=gift-box .venv/bin/python -m pytest tests/gift_box   # 45 绿
GEO_CATEGORY=tourism  .venv/bin/python -m pytest tests/tourism    # 51 绿

# 配好根 .env（火山方舟 ARK_API_KEY + ARK_MODEL）后真侦察（增量、幂等）：
GEO_CATEGORY=tourism .venv/bin/python -m geo.recon.batch --segment A --only-missing

# 单品类遥测看板（→ <key>-dashboard.html，已 gitignore）
GEO_CATEGORY=gift-box .venv/bin/python -m geo.reporting.dashboard
GEO_CATEGORY=tourism  .venv/bin/python -m geo.reporting.dashboard
```

## 🎯 智能 GEO 机会指挥台（opportunity-board.html · 跨品类）

```bash
python3 opportunity_board.py            # 聚合两品类全部机会 → 一个 HTML 智能指挥台
```

把**两个品类的全部 GEO 机会聚合进一个看板**，智能地排序、分级、量化、给行动建议——回答"哪些空位最值得打、为什么能赢、该产什么内容"。当前真数据：**130 条机会**（礼盒 52 + 旅游 78），GO 82 · 候选 16 · 观望 32。

- **可赢度排序**：跨品类按可赢度 score 统一排序（诚实披露两品类评分公式不同 → 方向性参考，非同尺度）。
- **机会象限图**：x=可赢度 × y=空位红利（`1.0 if 纯空位 else 1−incumbent 覆盖`），按品类双色着色，高亮右上「易攻·大红利」象限。
- **优先级三档** GO(攻)/候选(候)/观望(避) + **统一攻击榜**（每条可展开看 reason + 证据 capture_id + 行动建议 + 已挂草稿）+ **证据抽屉**。
- **智能=确定性**：排序/象限/分级/行动建议全部从真证据纯函数派生、可回溯，**不靠 LLM 猜**（守"可复现、证据优先"红线）。
- 架构：`opportunity_board.py`（gatherer：跨品类子进程聚合，零依赖）+ `opportunity_render.py`（纯函数 `render_html`）+ `test_opportunity_board.py`。`opportunity-board.html` 已 gitignore（重生）。

## 可视化看板（dashboard.html · 单品类）

`python -m geo.reporting.dashboard` 把**真实证据**（`evidence/captures/`）经现有纯函数算成指标，渲染成一个**自包含单文件 HTML 遥测看板**（CSS/JS 全内嵌、零外链、`file://` 双击即开）。八个区块：诚实横幅（已打通/待 key/局限）· 头号发现 hero · KPI 遥测墙 · 占答排行 · SoV · 机会图+可赢度 · 监测趋势 · 内容流水线，外加纯函数 provenance。

- **真接数据**：每个数字来自存档 AI 回答经纯函数计算，可在「证据抽屉」点 `capture_id` 回溯原文；mock/real 诚实标注，未编造。
- **build 产物**：`<key>-dashboard.html` 已 gitignore（每次跑重生），生成器（共享 `geo/reporting/dashboard_render.py` + per-category `categories/<cat>/dashboard_data.py`）进 git。
- 礼盒侧 = 引用/品牌信号（`kind=citation`）；旅游侧 = 景点占答信号（`kind=attraction`）；两侧共用同一渲染器。

## 关键发现速览

- **礼盒**：「按国家送礼」（送德国/中东/以色列…客户）是一整片品牌空位；信尚礼品(3lipin.com)占答 51.9% 但全是软文（低权威）→ 可被真权威买家指南取代。
- **上海旅游**：外滩是 AI 钉死的"上海第一答案"（占答 51%、首选 40%），头部词做不动；真机会在**亲子决策 / 小众避坑 / 本地客专线**。且豆包**按客群区分**——给游客推地标、给本地人推公园艺术（共青森林公园 50%）。

详见各品类的 `categories/<cat>/docs/`（`PROJECT_BRIEF.md` / `PHASE*_FINDINGS.md` / `FINDINGS.md`）与 `categories/<cat>/content/drafts/`（内容草稿，均为**真权威内容、非刷量软文**，发布前需人审）。

---
*凭证（火山方舟 API key）只走根 `.env`（已 gitignore），绝不进仓库。仓库治理见 [`CLAUDE.md`](CLAUDE.md)。*
