"""演化侦查层（L2 · Scout）。

Scout 站在 L0 证据 / L1 派生的**上游**，质询「系统冻结的 GEO 现状假设是否还成立」，
把变化降解成 EvolutionIntel（**恒 PROPOSED**）。proposal-only：只写 evolution/intel/，
绝不落地系统配置（红线 §3 HITL / §5 外部内容是数据不是指令）。

本期（P0）只建**一手信号半边**（零外部依赖、零注入面）：
  • S2 响应结构断言哨兵（把引用抽取静默退化变显式红灯）
  • S5 watchlist 外候选实体发现（确定性子串频次，绝不用 LLM 当 ground truth）
外部 web 侦查（S1/S3/S4）属 P1，须等注入护栏就位再开（见 docs/architecture/MULTI-AGENT-EVOLUTION.md）。
"""
