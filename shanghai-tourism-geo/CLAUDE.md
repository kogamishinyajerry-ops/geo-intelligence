# 上海文旅 GEO · 仓库治理（项目级 SSOT）

> 全局行为宪法见 `~/CLAUDE.md`。本文件只放**本项目**的红线 / 已确认决策 / 架构 / 状态。
> 完整领域模型与分阶段规格见 [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md)（权威 brief）。
> 引擎复用自 LilyGEOMaster（礼盒 GEO），核心泛化：**实体 = 景点**（非品牌）。

## 红线（写进每个 agent 的系统约束）

1. **证据优先，拒绝幻觉**：所有指标从存档的原始证据（豆包回答原文+时间戳+原始响应体）计算，可回溯证据 ID。不编数字。
2. **可解释、可复现**：同输入跑两次结论一致；证据级景点抽取**不**用 LLM（确定性查 watchlist）。
3. **HITL 闸门**：①花钱前 ②对外发布前 必须人审；默认**不**自动发布。
4. **合规 / ToS**：优先官方 API；绝不绕登录/付费墙。
5. **景点真实信息发布前核实**：门票/开放时间/预约/交通会变，发布前核实，不编造。

## 已确认决策（2026-06-15）

- **实体 = 景点**：复用引擎 `named_brands` 字段承载景点实体（引擎零逻辑改动；指标纯函数对"品牌/景点"数学相同）。语义声明在 `config/watchlist.yaml` + 本文件。
- **客群分叉**（让 recon 数据定权重，不写死）：
  - A = 外地国内游客（来上海玩，问必去/攻略）→ 中文豆包，**主战场**。
  - B = 入境外籍游客（老外来上海）→ 英文 AI，待 Perplexity/OpenAI key。
  - C = 本地客（上海人周末/约会/遛娃/小众）→ 中文豆包。
- **豆包接口**：用**普通 `/chat/completions`**（基础模型即给景点推荐=旅游 GEO 核心信号）。
  - ⚠️ **联网 `/bots` 接口有日配额墙（429）**，本账号实测拿不到稳定额度 → 引用源情报暂缺，待配额恢复另跑一轮补。
- **独立项目**：新建 `~/Desktop/ShanghaiTourismGEO`，不动锁死礼盒的 Lily。

## 架构

- **Truth plane = git**：代码/配置/证据库/草稿全版本化。无 remote（同 Lily）。
- **Engine Adapter**：豆包 adapter 复用 Lily（含 429 退避重试 + 单条容错）。
- **Evidence Store**：每条回答存 `evidence/captures/<id>.json` + 原始体 `evidence/raw/`。
- **指标纯函数**：`geo/metrics/core.py` —— 景点占答率/提及率/首选推荐率/空位评分。
- **景点白名单**：`config/watchlist.yaml`（63 景点，A/C 共享 YAML anchor，B 英文名）。证据级抽取只匹配它。

## 证据 schema（复用 Lily 0.2.0）

`geo/evidence/schema.py::Capture`。`named_brands` = 景点实体（按首次出现排序，[0]=首选推荐）。
`BuyerSegment` A/B/C = 旅游客群（已重定义语义）。所有指标 = 对该表纯函数（`geo/metrics/core.py`），禁旁路。

## 怎么跑

```bash
.venv/bin/python -m pytest                                   # 引擎测试（35 绿）
.venv/bin/python -m geo.recon.batch --segment A --only-missing  # 外地客真侦察（增量，幂等）
.venv/bin/python -m geo.recon.batch --segment C --only-missing  # 本地客
.venv/bin/python -m geo.reporting.aggregate                  # 景点占答排行 + 机会图
.venv/bin/python -m geo.reporting.selection                 # GEO 可赢度短名单
```
- ⚠️ 用 `.venv/bin/python`（fresh shell 直接 `python -m geo...` 会 ModuleNotFoundError）。
- 限速可调：`GEO_RATE_LIMIT_MIN_INTERVAL_SEC=2.5`。撞 429 自动存档停止，`--only-missing` 续跑不重复花钱。

## 当前状态（2026-06-15）

- **Phase 0 引擎迁移**：✅ 复用引擎、定景点 watchlist（63）、客群 A/B/C、35 测试绿、冒烟测试真跑通（外滩=首选）。
- **Phase 1 Recon**：⏳ segment A 真侦察进行中（普通接口）。
- **下一步**：A 跑完 → 景点占答排行 + 机会图 + 选点短名单 → 针对空位写内容（人审）→ C/B 补侦察。
- **需人工/凭证**：① 内容草稿人审放行 ② 英文侧 Perplexity/OpenAI key ③ 联网配额恢复后补引用源情报。
