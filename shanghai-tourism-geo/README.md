# Shanghai Tourism GEO

可审计、可复现的智能 **GEO（Generative Engine Optimization）** 工作流 —— 上海文旅景点版。
目标：测量「游客问豆包'上海去哪玩'时，AI 推荐了谁、谁是空位」，并自动跑通
「机会发现 → 选点/选主题 → 策略评估 → 内容运营 → 监测维护」闭环。

> 引擎复用自 [LilyGEOMaster](../LilyGEOMaster)（礼盒 GEO），核心泛化：**实体 = 景点**（非品牌）。
> 完整领域模型见 [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md)；仓库治理见 [`CLAUDE.md`](CLAUDE.md)。

## 这套系统能 / 不能做什么（最重要）

- ✅ 自动化**测量**：抓豆包对游客问题的真实回答 → 存档原始证据 → 算景点占答率/提及率/首选推荐率/内容空位。
- ✅ 找空位、产真权威攻略内容（人审后发布）、再测量，闭环迭代。
- ❌ **不**保证"进答案"，**不**刷好评、**不**铺假攻略（脆弱+会被降权+违规）。

## 架构

- **Truth plane = git**：代码 / 配置 / 证据库（原始抓取）/ 草稿，全部版本化、可审计。
- **Engine Adapter**：每引擎一个 `query() → capture() → parse()` connector，内置限速 + 429 退避。
- **Evidence Store**：每条回答存档，所有指标是对它的**纯函数**（`geo/metrics`）。
- **实体 = 景点**：证据级抽取只匹配 `config/watchlist.yaml`（63 景点白名单），确定性、可复现。

## 客群分叉（让 recon 数据定权重）

| 客群 | 是谁 | 引擎 |
| --- | --- | --- |
| A 外地国内游客 | 来上海玩，问必去/攻略/行程 | 中文豆包（**主战场**） |
| B 入境外籍游客 | 老外来上海 | 英文 AI（待 key） |
| C 本地客 | 上海人周末/约会/遛娃/小众 | 中文豆包 |

## 快速开始

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest                                       # 全绿

# 填好 .env（ARK_API_KEY + ARK_MODEL，火山方舟）后，真侦察：
.venv/bin/python -m geo.recon.batch --segment A --only-missing   # 外地客（增量、幂等）
.venv/bin/python -m geo.reporting.aggregate                      # 景点占答排行 + 机会图
```

## 凭证（绝不进仓库 · 红线）

`.env` 填 `ARK_API_KEY` + `ARK_MODEL`（火山方舟控制台）。`.env` 已被 `.gitignore`；密钥只走 env。
