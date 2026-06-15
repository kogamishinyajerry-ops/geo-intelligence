# Lily GEO · 仓库治理（项目级 SSOT）

> 全局行为宪法见 `~/CLAUDE.md`。本文件只放**本项目**的红线 / 已确认决策 / 架构 / 状态。
> 完整领域模型与分阶段规格见 [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md)（权威 brief）。

## 红线（写进每个 agent 的系统约束）

1. **证据优先，拒绝幻觉**：所有指标从存档的原始证据（回答原文+时间戳+原始响应体/截图+抽取的实体/引用/链接）计算，可回溯到证据 ID。不凭模型印象编数字。
2. **可解释、可复现**：同输入跑两次结论一致；每个评分附「为什么 + 证据 ID」。证据级抽取**不**用 LLM（确定性优先）。
3. **HITL 闸门**：①花钱前 ②对外发布前 必须人审；默认**不**自动发布。
4. **合规 / ToS**：优先官方 API；浏览器抓取封装在限速、守 ToS 的 adapter，绝不绕登录/付费墙；广告依法标注。
5. **kill-criteria**：每个品类/动作设里程碑 + 止损线，跑不动就砍。
6. **简单到同事能用**：复杂留后端，前台（Notion）只留清楚的卡片和按钮。

## 已确认决策（2026-06-14）

- **买家分叉**：让 recon 数据定 —— A/B 两假设都跑，不写死。
  - A = 中国人买来送老外客户 → 中文 AI + 抖音/淘宝货架
  - B = 老外自己买 → 英文 AI + Shopify
- **首个真实引擎**：豆包（火山方舟）。英文侧（Perplexity/OpenAI）凭证未到位 → 暂走 mock，一把 key 即切真。
- **可见度监测**：自建直连 adapter，不接现成 SaaS（自己存原始证据，满足红线 #1）。
- **栈**：Python + pydantic v2 + httpx + tenacity + pytest；truth plane = 本地 git（待接 GitHub remote）；control plane = Notion（MCP）。

## Notion 控制面 (IDs · 非密钥，可入仓)

- **控制塔**：https://app.notion.com/p/37fc68942bed819dad18f9aa7f465d3d （page `37fc6894-2bed-819d-ad18-f9aa7f465d3d`）
- **证据索引 Evidence Index**：https://app.notion.com/p/45e2d20901514c168be36983d5954132 （data_source `6118730f-f8cd-41f2-9b9c-cfe99386794a`）
- **机会图 Opportunity Map**：https://app.notion.com/p/4bc2107ed43a4fed97b218d8b5bd5a3b （data_source `d8299366-46f3-45d2-8ae9-cd2589f27135`）
- **内容看板 Content Board**：https://app.notion.com/p/6fc3737d4c1b46c590f2aa848e9a0ced （data_source `0c44abb2-6501-4073-b4af-0b8dea924c0a`）— 待审/已批/已发/待刷新/已下线；4 篇买家指南草稿已上为「待审」。
- **监测日志 Monitoring Log**：https://app.notion.com/p/e5cb1e34179c4d038e4d763a1f93783f （data_source `09aebb89-3f37-48f2-82e1-7deef78b69a9`）— 每轮监测一行；P1=品牌空位被占。基线（2026-06-14）已上。

recon driver 将来推 Notion 用上面的 data_source id（page 属性映射见各 DB 的 Capture ID/Query 等列）。

## 证据 schema（§5，已锁定）

`geo/evidence/schema.py::Capture`。所有指标 = 对该表的纯函数（`geo/metrics/core.py`）。禁止旁路。
扩展字段：`raw_capture_path`（API 无截图，归档原始响应体）、`is_mock`（诚实标注）、`engine_model/request_params/*_version`（可复现审计）。

## 怎么跑

```bash
pytest                              # 纯函数/schema/抽取测试
python -m geo.recon.run --mock-only # 无 key 跑通管道
python -m geo.recon.run --phase0    # 需 .env 里的 ARK_API_KEY + ARK_MODEL
```

## 当前状态

- **Phase 0（脚手架 + schema + 豆包 adapter + 最小切片）**：✅ DoD 达成，等用户 review。
  - [x] 仓库 + schema + Evidence Store + 指标纯函数 + 测试(12/12 绿) + 豆包/mock adapter + recon driver
  - [x] Notion 控制板骨架（控制塔 + 证据索引 + 机会图）
  - [x] 真实豆包跑通 1 条中文 query（model=doubao-seed-1-6-flash-250615, mock=False）→ 证据 JSON + Notion 3 行
- **豆包模型（火山方舟，账号 2114441818 已激活）**：直接用 model id，**无需** ep- 接入点。已激活：`doubao-seed-1-6-flash-250615`（快速版）/ `doubao-seed-1-6-250615` / `doubao-seed-1-8-251228` / `doubao-1-5-lite-32k-250115` / `doubao-1-5-pro-32k-250115`。
- **联网（ARK_BOT_ID）已配** `bot-20260614150734-98qkm`（联网内容插件，底层模型 doubao-1-5-pro-32k-250115）→ 走 `/bots/chat/completions`，回答带引用，含 `auth/rel/freshness` 分（schema 0.2.0 的 CitedSource）。
  - **实测确认**：① 商品卡 API **不返回**（C 端特性 → 国内商品卡信号需另走 C 端监测线）；② 联网触发**非 100%**（裸 query 高频命中；**勿加“请联网搜索”系统提示**，反而抑制触发）。
- 英文侧真实化：等 Perplexity/OpenAI key（adapter 接缝就绪）。
- **首个真实竞争发现**（礼盒中文 query）：`3lipin.com`（信尚礼品）占豆包引用 **4/10**、平均 auth **0.40**（软文为主）→ 高权威结构化买家指南可切入。
- **已知小修**：中文 watchlist 待策展（候选『万事利』『蜀锦』…）→ 对同一存档证据重算。（retry-4xx 已修。）

## Phase 1/2 完成（2026-06-14 · 自主开发）

- 批量侦察 12 query（segment A 豆包联网）→ 100 引用、21 测试绿、3 commit。
- **机会图 + 引用源排行 + 选品短名单 + 策略备忘** 全上 Notion + `docs/PHASE1_FINDINGS.md`。
- **关键发现（双空位）**：引用层 信尚礼品(3lipin.com) 占 8/12 但 auth~0.4（软文）；品牌层无伴手礼盒专门户。攻击 top-4 = 中国风/展会/非遗/茶（品牌空位+低权威）。
- 命令：`python -m geo.recon.batch --segment A`（侦察）· `geo.reporting.aggregate`（机会图）· `geo.reporting.selection`（选品）· `geo.recon.rederive`（改 watchlist 后重算品牌）。
- **下一步需人工/凭证**：英文侧 Perplexity/OpenAI key · 内容创作（HITL 闸门）· 供应链/毛利补全 go/no-go · M3 周期监测建时间序列。

## Phase 3/4 完成（2026-06-14 · 自主开发）

- **Phase 3 内容（HITL 闸门）**：top-4 query 各一篇高权威**买家指南**草稿（`content/drafts/01-04`），全部上 Notion 内容看板为「**待审**」、附 GEO 上稿依据（证据 ID + 可赢度 + 机会）。每篇要点先行 + 国别禁忌速查（标「发布前核实」）+ 价位分层 + FAQ + `[待补]` 品牌占位。**真权威内容，非软文**；事实项与品牌信息发布前人审，不编造。
- **Phase 4 监测（周期）**：`geo/monitoring/`：
  - `snapshot.py` 现有证据 → 派生指标快照（带 capture_ids 可回溯）→ `monitoring/history/<seg>-<utc>.json`。
  - `diff.py` 两快照 → 结构化变化 + 人读告警（P1 品牌空位被占 / P2 新对手·新品牌·联网消失 / P3 覆盖·权威·新鲜度·空位 移动）。纯函数，阈值集中可校准。
  - `run.py` 编排 snapshot→diff(vs 上次)→落告警/快照/Notion 队列。**默认不花钱**；`--refresh`（重查豆包）被 env `GEO_MONITOR_ALLOW_SPEND=1` 硬门控（红线：花钱前人审）。退出码 0/1/2（无变化/有告警/有 P1）。
  - **基线已立**（2026-06-14, segment A, 12 captures）→ Notion 监测日志 + `monitoring/history/`。
  - **调度**：`scripts/weekly_monitor.sh` + crontab `0 9 * * 1`（每周一 09:00 本地）。不占端口、不杀进程。告警先落本地（truth plane），Notion 镜像在会话内人工/MCP 完成。
- **测试**：35 绿（监测新增 14：snapshot 形态/可回溯 + diff 各信号 + run 纯函数）。
- **命令**：`python -m geo.monitoring.run --segment A`（监测一轮，不花钱）· `python -m geo.monitoring.snapshot --save`（仅存快照）· `./scripts/weekly_monitor.sh`（cron 入口）。

## Phase 5 完成（2026-06-14 · 自主开发 · 规模化）

- **侦察 query 12→34**：多维盲扫工作流（6 盲扫生成器+综合+对抗剪枝）→ 22 新 query 真实豆包侦察（180 引用，14/22 品牌空位）。`batch --only-missing` 增量侦察（不重跑/重复计数）。
- **竞争强化**：信尚礼品（3lipin.com）占答 8/12→**19/34（56%）**、被引 50、auth~0.5 软文 → 头号待取代。品牌 SoV：故宫文创 38%（超华为）/华为 29%/小米 14%/茅台 10%/万事利·五粮液 5%。
- **品牌已占 vs 内容空位（34 query=14 空位/15 已占/6 观望）**：丝绸=万事利·白酒=茅台·文创/价位/批量=故宫文创·圣诞=华为（**已占→避**）；分国别/场景/瓷器茶具/企业采购（**空位→本轮已上 4 篇内容**）。
- **4 篇主题制权威内容**（`content/drafts/05-08`，全上 Notion 内容看板待审）：分国别禁忌(印/德/美/法/韩)、商务场景(年终答谢 GEO 81 全场最高/出访见面礼)、瓷器茶具、企业批量定制采购。内容工作流 draft→**对抗式红线审计**，**全部 0 编造**，仅 P3 已自动修正。
- **监测基线重建**：12→34 cap（`snapshot --save`，不跑 diff 避假告警）→ Notion 监测日志。
- 全套 35 测试绿。详见 [`docs/PHASE5_FINDINGS.md`](docs/PHASE5_FINDINGS.md)。

## 可视化看板 dashboard.html（2026-06-15）

- `python -m geo.reporting.dashboard` → 自包含单文件 HTML 遥测看板，**真接证据数据**（52 caps 经现有纯函数算指标，零写死、可回溯 capture_id）。
- 文件：`geo/reporting/dashboard_data.py`（装配 payload，禁旁路）+ `dashboard_render.py`（纯函数 `render_html`，两品类共用、与旅游侧**字节相同**）+ `dashboard.py`（CLI）+ `tests/test_dashboard.py`（10 测试：契约形状/可回溯/可复现/真值渲染）。
- 八区块：诚实横幅（已打通豆包·待 key 英文侧·局限）· hero（69% 空位 + 软文 incumbent 可取代，数据派生）· KPI 遥测墙 · 引用源排行 · 品牌 SoV · 机会图可赢度 · 监测趋势 · 内容流水线 + provenance。`dashboard.html` 已 gitignore（重生），生成器进 git。
- **教训钩子**：① render JS 里 `const H` 重复声明 → 整脚本 SyntaxError 静默不渲染（所有 `—` 占位残留）；改 render 后**必 headless 渲染验 DOM**（`chrome --headless --dump-dom`），只验 `render_html` 返回串含子串会假绿。② hero/KPI 文案要 category-aware（payload 带 `hero`+按 `leaderboard.kind` 区分），别把礼盒"高空位"叙事套到旅游"低空位"上。③ 旧项目 `cp` 来的 .venv 带 stale editable `.pth`（指向旧 Desktop 路径）→ 跨 cwd import shadow，改 finder MAPPING 指向本地修复。

## 下一步路线（brief §6）

Phase 1 Recon 引擎 ✅ → Phase 2 分析/选品/策略 ✅ → Phase 3 内容流水线（人审）✅ → Phase 4 监测+调度 ✅ → Phase 5 规模化侦察+内容 ✅（发布待人审放行）。每阶段先验证证据为真再往上盖。
**剩余需人工/凭证**：① 内容草稿人审放行 + 填 `[待补]` 我方品牌信息 ② 英文侧 Perplexity/OpenAI key ③ 供应链/毛利补全 go/no-go ④ 准备好后开 `GEO_MONITOR_ALLOW_SPEND=1` 让每周监测真抓豆包最新答案。
