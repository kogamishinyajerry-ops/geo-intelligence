# GEO Intelligence · 仓库治理（项目级 SSOT）

> 全局行为宪法见 `~/CLAUDE.md`。本文件只放**本项目**的红线 / 架构 / 怎么跑 / 状态 / 教训。
> 一个共享引擎 + per-category 配置；品类靠环境变量 `GEO_CATEGORY` 选 active profile。
> 领域模型与分阶段规格见各品类 `categories/<cat>/docs/PROJECT_BRIEF.md`。

## 红线（写进每个 agent 的系统约束）

1. **证据优先，拒绝幻觉**：所有指标从存档的原始证据（回答原文+时间戳+原始响应体+抽取的实体/引用）计算，可回溯到 capture_id。不凭模型印象编数字。
2. **可解释、可复现**：同输入跑两次结论一致；证据级抽取**不**用 LLM（确定性查 watchlist）。
3. **HITL 闸门**：①花钱前 ②对外发布前 必须人审；默认**不**自动发布（`GEO_MONITOR_ALLOW_SPEND=1` 硬门控刷新）。
4. **合规 / ToS**：优先官方 API；绝不绕登录/付费墙；广告依法标注。
5. **kill-criteria**：每品类/动作设里程碑 + 止损线，跑不动就砍。
6. **简单到同事能用**：复杂留后端，前台只留清楚的看板。

## 架构（一个共享引擎 + per-category）

```
geo/                       共享引擎（品类无关；按 active_profile 参数化）
├ category.py              CategoryProfile 注册表 + active_profile()（读 GEO_CATEGORY，默认 gift-box）
├ config.py               get_settings() 按 active profile 解析 category_root/evidence_dir/watchlist_path
├ adapters/ evidence/{schema(A/B/C),store} metrics/core monitoring/ parsing/extract recon/{batch,run,rederive,queries}
└ reporting/              aggregate selection tourism（共享，懒读 profile.queries/shelf）· dashboard_render · dashboard(CLI 派发) · notion_payload · schema_ld(确定性 JSON-LD 生成纯函数+四红线校验) · schema(CLI 派发)
categories/<cat>/          品类数据 + 差异代码（gift_box / tourism）
├ queries.py(QUERIES) config/watchlist.yaml evidence/ monitoring/ content/ docs/
└ dashboard_data.py       该品类 build_payload（gift_box=引用/品牌信号 kind=citation；tourism=景点占答 kind=attraction）
opportunity_board.py      跨品类机会指挥台（gatherer：子进程按 GEO_CATEGORY 各跑一次 → 聚合）+ opportunity_render.py
tests/{gift_box,tourism}/  按品类分（各带 conftest 设 GEO_CATEGORY）
```

- **CategoryProfile**（`geo/category.py`）声明：segments / real / mock / use_search（联网 bot vs 基础模型）/ watchlist_keys / shelf / default_segment / queries / build_payload。
- **加新品类** = 加 `categories/<new>/`（queries+watchlist+evidence+dashboard_data）+ 在 `_PROFILES` 注册一条。引擎零改动。

## 怎么跑

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"

# 测试（按品类分别跑，env 选品类）
GEO_CATEGORY=gift-box .venv/bin/python -m pytest tests/gift_box   # 69 绿
GEO_CATEGORY=tourism  .venv/bin/python -m pytest tests/tourism    # 69 绿

# 真侦察（配根 .env：ARK_API_KEY + ARK_MODEL）
GEO_CATEGORY=tourism .venv/bin/python -m geo.recon.batch --segment A --only-missing

# 单品类遥测看板（→ <key>-dashboard.html，已 gitignore）
GEO_CATEGORY=gift-box .venv/bin/python -m geo.reporting.dashboard
GEO_CATEGORY=tourism  .venv/bin/python -m geo.reporting.dashboard

# 跨品类智能机会指挥台（→ opportunity-board.html）
.venv/bin/python opportunity_board.py

# 部署端：草稿 → 确定性 JSON-LD/Schema（→ content/schema/，已 gitignore；--validate-only 只校验）
# 真值靠 env 注入不编造：GEO_PUBLISHER_{BRAND,COMPANY,BASE_URL,LOGO,AUTHOR,TEL,SAMEAS,DATE}
GEO_CATEGORY=tourism .venv/bin/python -m geo.reporting.schema --validate-only
```

## 当前状态（2026-06-16）

- **两引擎已合并**为一个共享引擎 + per-category（消除重复）：69+69 测试绿；两品类豆包真证据（礼盒 52 / 旅游 78=A78）。
- **交付**：① 单品类遥测看板（8 区块，真接证据，可回溯）② 跨品类智能机会指挥台（130 机会 / GO 82，可赢度排序 + 象限图 + 攻击榜 + 证据抽屉）③ **部署端：确定性 Schema 生成器**（`geo/reporting/schema_ld`+`schema`）——草稿 → Article/ItemList/首页 JSON-LD，同输入字节级可复现，课程四红线写成 `validate_jsonld` 校验。生成 html/jsonld 为 gitignore build 产物，生成器进 git。
- **GEO 两端齐活**：测量端（recon→metrics 测占答率/空位）+ 部署端（schema 生成）。部署端知识 canon 见 `Lessons/GEO课程·深度学习笔记.md`（视频萃取，含证据帧）。
- **关键发现**：礼盒「按国家送礼」整片品牌空位、信尚礼品占答 52% 软文可取代；旅游外滩钉死头部（占答 51%/首选 40%），机会在亲子/小众/本地客长尾。
- **需人工/凭证**：① 内容草稿（gift 10 / tourism 4）人审放行 ② 英文侧 Perplexity/OpenAI key（B 段）③ 旅游联网配额恢复后补引用源情报。

## 教训钩子（load-bearing）

- **render JS 变量名重复声明**（`const H` 撞已有）→ 整脚本 SyntaxError → 全页静默不渲染（满屏 `—` 占位）。改 render 后**必 headless 渲染验 DOM**（`chrome --headless --dump-dom` 看节点真填充），只验 `render_html` 返回串含子串=假绿。
- **共享引擎接缝 = 运行时读 active_profile**：模块级常量（`_THEME`/`SHELF`/路径）若用 active_profile 算会在 import 时**锁死品类** → 全部改函数内懒算。import 循环（category↔config）靠函数内 import 化解。
- **旧项目 cp 来的 .venv** 带 stale editable `.pth`（指旧 Desktop 路径）→ 跨 cwd import shadow；重指 finder MAPPING 或重建 venv。
- **别对未提交的证据/数据 `git clean`**：合并期 evidence/monitoring 是 untracked，`git clean` 会清掉真数据（已踩，从 checkpoint 恢复）。
- **JSON-LD 是严格 JSON，`//` 注释非法**（课程视频演示带注释会害人）→ schema_ld 输出的是无注释合法 JSON，证据/说明走外层 HTML 注释（在 JSON 体外）。校验器 `validate_jsonld` 把课程四红线（单页面单 Schema / desc≤150 / ISO 日期 / 不得含广告）写成可执行规则，有 ❌ 则 CLI 非零退出（fail-closed）。
- **Schema 只对自有站点有效**：草稿"建议平台"多是小红书/知乎/携程等第三方，**无法注入 `<script ld+json>`**；schema CLI 未配 `GEO_PUBLISHER_BASE_URL` 时会打印此边界提示。我方信息一律 `[待补·HITL]` 占位、靠 env 注入真值，**绝不编造**（红线§1）。

## 凭证

火山方舟 API key 只走根 `.env`（已 gitignore），绝不进仓库。`.env.example` 是模板。
