# Lily GEO

可审计、可复现的智能 **GEO（Generative Engine Optimization）** 工作流。
目标：自动跑通「机会发现 → 选品 → 策略评估 → 内容运营 → 监测维护」闭环。
第一个落地品类：**面向商务场景的高端伴手礼盒**。

> 完整领域模型、原则与红线见 [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md)。
> 仓库治理（红线 / 已确认决策 / 状态）见 [`CLAUDE.md`](CLAUDE.md)。

## 这套系统能/不能做什么（最重要）

- ✅ 自动化**测量**：抓 AI 答案引擎的真实回答 → 存档原始证据 → 算占答率/提及率/首选推荐率/空位评分。
- ✅ 找空位、产真权威内容（人审后发布）、再测量，闭环迭代。
- ❌ **不**保证「进答案」，**不**注入广告、**不**铺假软文（脆弱+会被降权+违广告法）。

## 架构

- **Truth plane = git**：代码 / 配置 / 证据库（原始抓取）/ 草稿，全部版本化、可审计。
- **Control plane = Notion**：机会图 / 选品 / 策略 / 内容看板 / KPI / 审批闸门（同事在此操作）。
- **Engine Adapter**：每引擎一个 `query() → capture() → parse()` connector，内置限速。新增引擎 = 加 adapter，不动主流程。
- **Evidence Store**：每条回答存档，所有指标是对它的**纯函数**（`geo/metrics`）。

## 目录

```
geo/
  config.py            # 凭证/参数（仅 env / .env）
  evidence/schema.py   # Evidence schema（§5，已锁定）
  evidence/store.py    # JSON-per-capture，git 友好
  adapters/base.py     # EngineAdapter 基类（限速 + capture 编排）
  adapters/doubao.py   # 豆包（火山方舟）— 真实
  adapters/mock.py     # 占位（英文侧凭证到位前）
  parsing/extract.py   # 确定性抽取（链接/品牌/引用）
  metrics/core.py      # 占答率/提及率/首选推荐率/空位评分（纯函数）
  recon/queries.py     # 礼盒品类买家高意图问题
  recon/run.py         # 端到端 recon driver（CLI）
config/watchlist.yaml  # 品牌观察名单（证据级品牌抽取的唯一来源）
evidence/              # 证据库（captures/ + raw/），版本化
tests/                 # 纯函数 / schema / 抽取 测试
```

## 快速开始

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                                   # 全绿

# 无需任何 key，跑通全管道（证明管道为真）：
python -m geo.recon.run --mock-only

# 填好 .env（ARK_API_KEY + ARK_MODEL）后，中文豆包真跑：
cp .env.example .env      # 然后编辑 .env
python -m geo.recon.run --phase0
```

## 凭证（绝不进仓库 · 红线 §7）

`cp .env.example .env`，填 `ARK_API_KEY` + `ARK_MODEL`（火山方舟控制台）。
`.env` 已被 `.gitignore`；密钥只走 env，不进仓库、不进聊天。
