# geo-intelligence 多 Agent 演化架构 · SSOT

> 状态：**设计已定稿，P0 施工中**（branch `feat/multiagent-evolution-p0`，2026-06-16 起）。
> 本文件是这条演进线的唯一真相源。施工以此为准；与本文件冲突的口头/记忆描述以本文件为准。
> 全局行为宪法见 `~/CLAUDE.md`，仓库治理见根 `CLAUDE.md`，本文件只管「多 agent 演化架构」这一条线。

---

## 0. 这份文档解决什么问题

geo-intelligence 现在是一条直线流水线（recon → parse → evidence → metrics → reporting → opportunity → deploy）。
两个判断驱动它演进：

1. 它可以变成一套**多 Agent 协作架构**。
2. GEO 这门生意是**非稳态**的——引擎、引用机制、schema 规则、竞品打法、行业工作流都在持续变。不是一劳永逸的架构。

因此需要一个**专门侦查 GEO 演化的 Agent（Scout）**，把外部世界的变化降解成对系统冻结假设的变更提案，反馈进系统。

**深挖后的诚实裁决**：现在真正值得独立成 agent 的只有 **2 个**（不是一支舰队）。其余保持纯函数 + 调度脚本。多 agent 的真实增益要等触发条件成立才兑现（见 §6）。

---

## 1. 核心组织原则

> **证据冻结 · 派生可重放 · 演化经治理 —— LLM 与「外部世界」被关进唯一一个 proposal-only 的笼子，笼子的锁是已验证过的 fail-closed gate。**

唯一组织维度 = **信任层**（不是品类/功能/生命周期）。三个同心层，每层一条可机器检查、违反即废案的不变式：

| 层 | 是什么 | 不变式（可机器检查） |
|---|---|---|
| **L0 证据平面** | `categories/<cat>/evidence/captures` + `raw/`，append-only | id 内嵌 `sha10(raw_answer)`；`is_mock` 由 adapter 类属性自动传播；**任何 agent 只读，唯一写入者 = 确定性抓取工序** |
| **L1 确定性派生** | extract / metrics / diff / reporting / schema_ld | 纯函数；同输入 → 同字节输出；**绝不用 LLM**；fail-closed |
| **L2 演化治理** | Scout 侦查 + 机器门 + HITL + 异源审 | **LLM 与外部内容只活在这一层，且产出永远是 proposal 不是 mutation** |

**铁律一**：没有任何 agent 同时持有「写证据」与「重配置系统」两种权力 → 直接挡住诚实崩塌。
**铁律二**：演化层产出落 `evolution/intel/`，是 `proposal` 不是 `git commit`；外部网页文字进系统后**永远是字符串，绝无 eval / 指令执行路径**（红线#5 落到架构层，不靠提示词）。

为什么不选另外三个轴：信任层是唯一既能组织、又能把六条红线变成可机器检查不变式的轴。其余三轴（流水线阶段 / 客户生命周期 / 演化神经环）切出的边界都会在「谁能写证据 / 谁能改配置 / LLM 能碰哪层」上模糊掉。

---

## 2. Agent 名册

| 角色 | 身份 | 自主度 | 触发 | 何时建 |
|---|---|---|---|---|
| **🛰️ Scout（演化侦查）** | **真 agent** | 侦查全自动 + 提案恒 HITL，**零执行权** | 内部信号事件优先 + 低频周期兜底 | **P0（一手信号半边）** |
| **Watchlist-Curator** | 真 agent | proposal-only + HITL | Drift 报新对手 / 周期 | **P1**（数据多到人工扫不动再建） |
| **Red-line Gate** | **不是 agent，是闸** | 全自动拒绝，**从不批准** | 任何落地/提案前 | **P0** |
| Capture / Drift / Orchestrate / Analyst / Schema-Deploy / Synthesizer | **确定性工序/脚本** | 信号触发、出退出码 | — | **保持纯函数，永不 agent 化（除非触发阈值成立）** |

**克制裁决（最重要一句）**：当前 N=1 真引擎（豆包）、2 品类、288 capture。把已是 CLI + 纯函数的东西升格为长寿命 agent 是叙事对称，不是工程需要。**为什么 Capture/Drift/Analyst/Synthesizer 不是 agent**：它们零自主决策、纯函数挂触发，叫「agent」只是术语通胀。

---

## 3. 🛰️ Scout — GEO 演化侦查 Agent（核心）

> 它不在数据流里。它站在 L0/L1 **上游**，质询「系统冻结的那些 GEO 现状假设是否还成立」。系统今天「能优雅承接演化（seams 齐全）但不知道何时该演化（无 Scout）」——Scout 补的正是这个元层。

### 3.1 单一职责
持续侦查 GEO 战场非稳态信号 → 定位「系统里哪条冻结假设正在过期」→ 产**结构化演化情报 + 具体到接缝的变更提案** → 经机器门 + HITL 反馈进系统。**只提案，绝不自行落地，零写权限（除自己的 `evolution/intel/` 隔离命名空间）。**

### 3.2 监测信号源（分层 × 映射到系统哪条冻结假设）

| 层 | 侦查什么 | 对应冻结假设（代码接缝） | 过期后果 |
|---|---|---|---|
| **S1 引擎层** | 新引擎入场（Kimi/夸克/DeepSeek/文心/AI Overviews） | `geo/category._PROFILES` 只 DoubaoAdapter 真跑，余 mock | 整个战场没被测量 |
| **S2 机制层** | 引擎改检索/引用/排序（何时联网、引用谁、权威/新鲜度加权） | `use_search` 二值位、豆包深路径 `_parse_references`、auth/freshness 透传 | **引用抽取静默归零、可赢度失真且无告警** |
| **S3 schema 层** | schema.org/富媒体/各引擎对结构化数据采纳偏好变化 | `validate_jsonld` 四红线、`_AD_TERMS`、`MAX_DESCRIPTION=150` | 部署产物不再被采纳/被判违规 |
| **S4 工作流层** | GEO 打法变 + **战场类型分裂**（GEO 问答 vs 本地 AEO） | `PROJECT_BRIEF.md` 地基事实、segment 划分、`battlefield_type` | 整套打法地基失真 / 在错误地图上侦查 |
| **S5 竞品层** | 新对手/新问法/季节热点 | `queries.py` 静态 list、`watchlist.yaml` STARTER | 监测越久越漏新进入者（假阴性） |

**刻意排除**：评分阈值（winnability 权重 `0.5/0.3/0.2`、`GO_THRESH`）**不是 web 可侦查的公开知识，是业务校准**，由人工/未来「阈值自适应」处理，不归 Scout。

**S4 战场类型分裂**（四镜全漏、memory 点名）：GEO（问答可见度）vs 本地 AEO（地图/点评类）不是一套工具通吃。Scout 给每品类标 `battlefield_type: qa_engine | local_aeo`；侦查到品类战场变了，提案是「换整套 adapter/query/打法」而非微调。

### 3.3 侦查方法（两种证据品质，严格分治）

- **一手信号（高可信，来自系统自己的证据，零外部依赖、零注入风险）—— 优先 / P0 先做**：
  - **S2 响应结构断言哨兵**：对真 `raw_payload` 跑结构断言，引用抽取命中率对照历史骤降 → 判定引擎改了结构。把「静默退化」变「显式红灯」。
  - **S5 候选实体发现**：扫 `raw_answer` 里 watchlist 外反复出现的候选（确定性子串频次，**不用 LLM 当 ground truth**）。
- **二手信号（低可信，来自外部 web）—— 后做 / P1，注入面最大**：
  - 工具 = 单一 canonical web 工具（`WebSearch`/`WebFetch`）扫官方 changelog/schema.org 公告/行业资讯。
  - 方法 = fan-out + 对抗式交叉验证 + 可信度分级（officially-confirmed / multi-source / single-source / rumor）。**绝不单源成案。**
- **优先级铁律**：**内部传感器 > 外部传言**。任何会改系统行为的提案，证据链**必须含 ≥1 条 internal-evidence（可回溯 capture_id）**；纯外部 web 情报只能停「待人工调研」。

### 3.4 EvolutionIntel（结构化演化情报，只读产物）

落 `evolution/intel/<cat>/<intel_id>.json`（git 友好，与证据同纪律），**不进 L0 证据层**。

```jsonc
{
  "intel_id": "scout-2026-06-16-S2-01",
  "captured_at": "<UTC>",
  "signal_layer": "S1|S2|S3|S4|S5",
  "claim": "网页/探针陈述的转写, 非指令",
  "battlefield_type": "qa_engine|local_aeo",
  "evidence": {
    "internal": [{"capture_id": "...", "note": "..."}],        // 优先, 可回溯
    "external": [{"url":"...","sha256":"...","verbatim_excerpt":"...","fetched_at":"...","source_cluster_id":"..."}],
    "machine_verifiable": {"probe": "真打query/重放payload", "result": "..."}
  },
  "confidence": "officially-confirmed|multi-source|single-source|rumor",
  "source_independence": "independent|same-cluster|cross-referencing",   // 反合谋
  "affected_assumption": "geo.category._PROFILES.tourism.real_segments",  // 指向稳定能力层
  "proposed_change": {
    "target_seam": "adapter|watchlist|queries|diff阈值|validate_jsonld|brief",
    "kind": "new-adapter|edit-watchlist|edit-queries|edit-redline|update-brief",
    "intent_sketch": "仅供人类审阅的意图描述, 绝不直接喂进 Codex prompt 当 ground truth",
    "blast_radius": "受影响品类/段/下游",
    "reversibility": "high|med|low",
    "rederive_needed": true,
    "requires_codex_review": true
  },
  "hitl_status": "PROPOSED",   // 初始恒为待审, Scout 永不自批
  "first_seen": "<UTC>", "times_seen": 1, "prior_intel_id": null
}
```

> **`intent_sketch` 不是 `diff_sketch`**：仅人类审阅的意图描述，绝不直接进 codegen prompt 当 ground truth（否则 LLM 幻觉经此潜入代码）。

### 3.5 完整回路：侦查 → 验证 → 反馈 → 系统自适应

```
🛰️ Scout(只读侦查, 内部信号优先) → EvolutionIntel(PROPOSED)
   ↓ 自验证: 每条claim跑零成本内部探针证伪 (探针不过→降rumor, 不可APPROVE)
        ▼ 只写 evolution/intel/ (零写系统配置)
   ╔═ Red-line Gate 机器门 (fail-closed) ═╗  按kind跑硬校验, ❌即打回不进人门
   ╚═══════════════┬══════════════════════╝
        PASS ▼
   ╔═ 异源审 (Codex, 仅代码/红线常量, cap=3) ═╗
   ╚═══════════════┬══════════════════════╝
     APPROVE ▼
   ╔═ HITL 人审闸 (红线#3) ═╗ ← 人是唯一签发者, 按 reversibility/blast_radius 分流
   ╚═══┬═════════════┬═════╝
APPROVED▼             ▼REJECTED→归档+记衰减
   确定性脚本落地 (隔离worktree, 非agent自由发挥), 按kind路由:
   S1 new-adapter → Codex写子类+_PROFILES注册 → 解析正确性oracle过 → mock冒烟
   S2 edit-adapter → 改解析路径/use_search位
   S3 edit-redline → 加一条validate_jsonld规则 (宁严勿松)
   S4 update-brief → 改地基事实/标battlefield_type
   S5 edit-watchlist → 经Curator确定性写yaml → rederive
   S5 edit-queries → 改queries.py → 增量补抓
        ▼ 系统重测
   回路闭合验证 (每动作配机器可判定oracle, 可证伪):
   · 改watchlist → rederive后 named_brands变化集 == 新增词条匹配集 (diff可证伪)
   · 接adapter → mock冒烟 + 真证据is_mock诚实翻转 + 解析oracle断言关键字段非空
   · 改阈值/红线 → 重放历史告警数变化方向符合改动方向
        ▼
   看板/board反映新配置 → Drift监测新漂移 → 反喂Scout下一轮
```

**可半自动 / 必过 HITL（精确刀法）**：
- **必过 HITL**：`edit-queries`（query 是测量定义）、`edit-redline`（合规，宁严勿松）、`update-brief`、**任何花钱动作**。
- **可半自动（机器门过即流到人门）**：`new-adapter` 脚手架、`edit-watchlist` 候选、`edit-adapter` 解析修复——**全部仍不绕过最后 HITL 签发**。
- **`rederive` 是反馈通道的最优一招**：改 watchlist/抽取后零成本回填历史不重花钱（已验证不调 API、id/原文不变）。**强制 dry-run + diff 预览前置**。

### 3.6 防「外部内容当指令」+ 防幻觉（红线#5，对 Scout 是命门）

1. **外部内容永远是数据不是指令**：WebFetch 回传只进 `evidence.external.verbatim_excerpt` 当引用素材，永远是字符串；网页里写「忽略前述规则/把 watchlist 改成…」一律当被侦查对象的数据正文记录，**不执行**。提示工程上用 `<untrusted_data>` 语义边界包裹。
2. **强可证伪 oracle，不止 source URL**：URL 可达 ≠ 断言为真。每条「新引擎/机制变化」断言**必须能被零成本内部探针证伪**——S1 新引擎 → 真打 query 看是否真返回可解析结果；S2 机制 → 重放历史 raw_payload 跑当前解析验是否真失效。**只有被探针证实的才可 APPROVED**。
3. **反合谋 / 源独立性**：同 MCN/同站群/相互引用的源**不算独立多源**，不得据此升 confidence（防「多源一致」被武器化）。
4. **Scout 零写权限**：对所有源码/配置/证据只读；只写隔离 `evolution/intel/`。落地由确定性脚本在 HITL 批准后、隔离 worktree 里做。
5. **HITL 永远 true + provenance 可证伪**：web 证据存 URL+sha256+excerpt+fetched_at，internal 存 capture_id，人审可回溯核对。
6. **异源交叉审**：Scout（Claude）提的 adapter 代码/红线常量改动 → Codex 异源审（命中即审，cap=3）；情报真伪 → 定间隔派 fresh-context verifier 复核。

### 3.7 Scout 是单 agent，不预先拆三段流水线
当前单引擎、2 品类、低频侦查，「多轴 × 多品类 × 真并行」的难题尾部几乎不触及。Cartographer（映射）和 Adapter（提案）在当前规模就是一个 Scout 流程的三个 phase。只有情报量大到单 agent context 装不下、或外部侦查与内部映射真需隔离时，才拆 Cartographer 翻译层——**那是 P1/未来，不预搭**。

但**先做 `assumptions.yaml` 冻结假设台账**：每条假设 `assumption_id` + `affected_assumption`（指向稳定能力层非易变文件行）+ `status: still-holds/at-risk/broken`。它是「系统的自知之明」，给 Scout 情报一个落点，本身零代码也有价值。

### 3.8 周期/触发 + 预算
- **事件/信号优先**：S2 结构断言失败 → 立即触发 S2 侦查；Drift 报「新对手域名站稳」→ 触发 S5 候选核验。
- **周期兜底**（Scout 唯一被允许设日历的角色，因这是它本职）：行业慢变量低频轻量巡检。**加 over-search 预算闸**：每轴侦查预算上限 + 「信号没变就别查」。外部 web 侦查须有等价 `GEO_MONITOR_ALLOW_SPEND` 的花费 fail-closed 门。
- **人审带宽预算**（HITL 非无限容量）：每周进人审队列提案数上限 + 按 reversibility/blast_radius 自动分流。
- **情报时间序列**：`first_seen/times_seen/prior_intel_id` 去抖合并；REJECTED 后设冷却期才可重提。

---

## 4. 协作协议与数据流

### 4.1 谁调谁（严格单向，无环）
```
Scout(L2) ── EvolutionIntel ──▶ Red-line Gate ──▶ Codex异源审 ──▶ HITL
                                                                    │ APPROVED
                                                                    ▼ 确定性脚本落地(隔离worktree)
   ┌──── 重配置(改query/adapter/watchlist/阈值/红线) ────┘
   ▼
Orchestrate脚本 ──▶ Capture工序[doubao(+未来引擎)] ──写──▶ L0证据(冻结)
                                                          │ 只读
   ┌──────────────────────────────────────────────────────┤
   ▼ L1纯函数(extract/metrics/diff/reporting/schema_ld)     ▼
Drift工序 ──退出码0/1/2──▶ (人看) ──▶ 决定是否叫Scout    Analyst/Synthesizer/Schema-Deploy
Watchlist-Curator(P1) ──候选──▶ Scout内部信号源 ──────────▶ (回喂上游)
```
> Drift 报 P2 → **人看 → 人决定叫不叫 Scout**，**不做自动反向触发**（在 Scout 还半自动阶段引入自动反向触发是过早编排）。

### 4.2 共享什么状态 / 如何不共享可变状态
- **唯一共享真相源 = L0 证据平面，append-only 冻结**。所有角色读它，**只有 Capture 工序写它**，按 `{engine}:cid` 命名空间物理隔离。共享的是**不可变事实**。
- **每个角色写自己命名空间**：Capture→`evidence/`、Drift→`monitoring/`、Scout→`evolution/intel/`、Curator→`watchlist_candidates/`。无两个角色写同一文件。
- **角色间通信走文件契约，不走共享内存**：JSON-per-item，git 友好，≤2000 token 摘要回传，原始 log 留各侧。
- **写操作并行 = 隔离 worktree + merge**，绝不并行直改同一文件。
- **per-category 隔离**：同名 geo 包不能同进程 import → 沿用 `.venv/bin/python -c` + `GEO_CATEGORY` env 子进程隔离（board 已验证）。

### 4.3 整体数据流（一句话）
外部世界变化 → Scout 只读侦查转译成带证据提案 → Red-line 机器门 + Codex 异源审 + HITL 三闸 → 确定性脚本落地为 query/adapter/watchlist/阈值/红线改动（隔离 worktree）→ Orchestrate 调 Capture 把引擎答案写进 L0（唯一真相源，冻结）→ L1 纯函数重算 → Drift/结构断言/Curator 三类内部硬信号回喂 Scout，闭合「侦查→反馈→自适应」。**证据永远冻结、派生永远可重放、演化永远经治理。**

---

## 5. 与现有代码的接缝（复用清单）

| 角色 | 直接复用 | 新增（最小） |
|---|---|---|
| Capture 工序 | `EngineAdapter.run()`、`EvidenceStore`、`parsing/extract`、`batch._missing` 续跑 | 写入后 sha10 自校验；新引擎 = Codex codegen 子类 + **解析正确性 oracle** |
| Drift 工序 | `monitoring/{snapshot,diff,run}` 纯函数、退出码协议 | 消费现成 `dropped_domains/dropped_brands/auth_moves`（P0#1）；去抖记忆 |
| Orchestrate 脚本 | opportunity_board 子进程模型、`ALLOW_SPEND` 闸、`--only-missing` | cron/调度脚本；**花钱闸前移到 recon.batch**（P0#3） |
| Red-line Gate | `validate_jsonld`（已对抗加固）、`schema` CLI 非零退出 | 升格统一机器门 + 接 Scout 回路（P0#4） |
| Watchlist-Curator | `parsing/extract`、`rederive`（dry-run 回填） | 候选发现 + proposal 契约 + 确定性写 yaml 脚本（P1） |
| Scout | `evidence/raw`、`rederive`、`WebSearch`/`WebFetch`、`_PROFILES`/watchlist/queries/validate_jsonld 当落点 | `evolution/intel/`、`assumptions.yaml` 台账、内部探针、提案路由器（P0 一手半边） |

---

## 6. 诚实的落地次序（reality check）

### P0 — 现在就值得建（零分歧、代码已验证、低成本高信噪比）
1. **Drift 消费空插座**：`dropped_domains/dropped_brands/auth_moves` 在 `diff_snapshots` 已算出，`build_alerts` 签名不收 → 纯加规则、零改 diff 计算。
2. **双注册表收敛单 SSOT**：`_PROFILES`（运行时）vs `opportunity_board.CATEGORIES`（展示）→ **第一步而非前置债**（Scout 加品类/加引擎是最高频触发漂移的动作）。用 safe-refactor 协议，注意别让 title/score_basis 污染引擎层品类无关性。
3. **修花钱闸覆盖盖**：`GEO_MONITOR_ALLOW_SPEND` 只守 `monitoring --refresh`，`recon.batch` 直接真跑只过 `require_ark()` → **把花费确认前移到 recon.batch / recon.run --phase0**。
4. **Red-line Gate 升级统一机器门**：复用已对抗加固的 `validate_jsonld`，几乎零新代码，是治理脊柱。
5. **Scout 一手信号半边先行**：S2 响应结构断言哨兵 + S5 候选实体发现 + `assumptions.yaml` 台账——风险最低、收益最直接的半边。

### P1 — 有数据后才值得
- Scout 二手信号（外部 web，S1/S3/S4）：注入面最大，**必须等 §3.6 注入护栏全建好 + P0 内部信号地基就位再开**（冷启动时内部信号近乎空，先开外部轴会退化成纯 WebSearch 驱动 = 最危险形态）。
- Watchlist-Curator：等证据量大到人工扫不动、名单外实体多时。
- Cartographer 翻译层拆出：等单 Scout context 装不下。

### 未来 — 信号到位再说（给可证伪触发阈值，不靠日历）
- Capture 多实例 + Orchestrate agent 化：触发 = **第二个真引擎凭证就绪**（不是「3 个引擎」这种无依据数字）。
- 评分阈值自适应校准：触发 = 历史快照样本量够大、方差可估。
- Content-Author（产对外内容）：触发 = 测量 + 侦查闭环稳定、护栏就绪。

### 不该建（保持纯函数/cron，不为多 agent 而多 agent）
- Recon-Orchestrator 长寿命编排循环、Drift/Analyst/Schema-Deploy/Synthesizer 升 agent、Query-Curator 独立 agent。
- loop-auditor + fresh-verifier + Codex + 机器门四层全开（COMAC 级长程配置，对个人项目过重）。起点 = Red-line 机器门（自动）+ HITL（人审）+ 涉代码时 Codex。

**演进路径**：先把 P0 五件做完 → 跑一个**最小可证伪实验**证明多 agent 真赚 → 再依信号开 P1。

---

## 7. 风险与失败模式

| 风险 | 级别 | 缓解 |
|---|---|---|
| Scout 把外部内容当指令（红线#5 命门） | 🔴 致命 | `<untrusted_data>` 边界 + 零写权 + 无证据即废 + HITL 永 true + proposal≠commit + 内部探针证实才 APPROVE |
| Scout 慢性中毒（多源合谋抬 confidence） | 🔴 致命 | `source_independence` 标注：同站群/相互引用不算独立多源 |
| Scout 幻觉一个不存在的引擎/规则就触发重配置 | 🔴 致命 | 强可证伪 oracle（真打 query/重放 payload），URL 200 ≠ 为真；机器门+Codex+HITL 三闸 |
| LLM 抽取污染 L0/L1（红线#2 崩塌） | 🔴 死罪 | LLM 只在 L2 且 proposal-only；Curator 写 yaml 走确定性脚本；别名也逐条人审 |
| fail-open 假绿（空集 PASS / 三元兜底） | 🔴 死罪 | Red-line Gate fail-closed；S2 结构断言把「静默归零」变显式红灯 |
| 新 adapter 解析正确性无验证 | 🟠 高 | 强制「解析正确性 oracle」：对真样本断言关键字段非空，否则不许 is_mock=False 落 L0 |
| S2 结构断言假阴（机制漂移 vs 联网未触发混淆） | 🟠 高 | 结合 use_search 状态 + 多轮归零率趋势，单轮归零不报机制漂移 |
| 人审退化橡皮图章（HITL 非无限容量） | 🟠 高 | 每周提案数上限 + 按 reversibility/blast_radius 自动分流 |
| rederive 批量污染 + 审计变难 | 🟠 高 | rederive 前强制 dry-run + diff 预览；派生可逆 |
| 双注册表漂移在多 agent 下放大 | 🟠 高 | P0 第一步就收敛 |
| 战场类型错配（GEO vs 本地 AEO） | 🟡 中 | Scout S4 标 `battlefield_type` |
| 成本/配额失控（个人额度敏感） | 🟡 中 | 花钱闸全覆盖；Scout 外部侦查 over-search 预算上限；官方 API only |
| 冷启动：内部信号近乎空 → Scout 退化纯外部驱动 | 🟡 中 | 落地次序铁律：P0 先建内部信号 + 注入护栏，P1 才开外部轴 |
| 过度编排负债（12-agent 幻想） | 🟡 中 | 现在只 2 真 agent + 1 机器门，其余纯函数/cron |

**最后一条 must-have**：不能停在架构图。落完 P0 必须做一个**最小可证伪实验**证明多 agent 真赚（例：Drift 消费空插座后用历史快照对跑，是否真捕到之前漏的对手退出/权威度信号）。给 Scout 配 **precision（提案采纳率）+ recall 代理（漏报）+ 单条情报成本账本**，否则无法自我校准。

---

## 附：本文档来源
由两段多 agent 工作流综合而成（2026-06-16）：① 架构设计（6 reader 映射代码 → 4 镜独立设计 → 对抗评分 + 完整性批评 → 首席综合）；② P0 接缝分析。决策档案见 git 历史与 transcript。
