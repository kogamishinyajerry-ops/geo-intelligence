"""Runtime config. Secrets come from .env / env vars only (红线 §7)."""
from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # ── 火山方舟 / 豆包（中文侧真实引擎）──
    ark_api_key: str | None = Field(default=None, validation_alias="ARK_API_KEY")
    ark_model: str | None = Field(default=None, validation_alias="ARK_MODEL")
    ark_base_url: str = Field(
        default="https://ark.cn-beijing.volces.com/api/v3", validation_alias="ARK_BASE_URL"
    )
    ark_bot_id: str | None = Field(default=None, validation_alias="ARK_BOT_ID")

    # ── 英文引擎（暂占位）──
    perplexity_api_key: str | None = Field(default=None, validation_alias="PERPLEXITY_API_KEY")
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")

    # ── 运行参数 ──
    rate_limit_min_interval_sec: float = Field(
        default=1.5, validation_alias="GEO_RATE_LIMIT_MIN_INTERVAL_SEC"
    )
    http_timeout_sec: float = Field(default=60.0, validation_alias="GEO_HTTP_TIMEOUT_SEC")
    max_retries: int = Field(default=3, validation_alias="GEO_MAX_RETRIES")

    # ── 路径（随 active profile 解析；下方默认仅占位，get_settings 会覆盖）──
    category_root: Path = Field(default=REPO_ROOT)
    evidence_dir: Path = Field(default=REPO_ROOT / "evidence")
    watchlist_path: Path = Field(default=REPO_ROOT / "config" / "watchlist.yaml")

    def require_ark(self) -> None:
        """火山方舟真实跑前的硬校验——缺凭证则明确报错，绝不静默回退到假数据。"""
        missing = [
            k
            for k, v in {"ARK_API_KEY": self.ark_api_key, "ARK_MODEL": self.ark_model}.items()
            if not v
        ]
        if missing:
            raise RuntimeError(
                f"缺少火山方舟凭证: {', '.join(missing)}。"
                f"请 `cp .env.example .env` 并填写后重试。"
            )


# ── 花钱闸（spend-gate）：真打付费引擎前的硬门控 SSOT（红线 §3：花钱前人审）──
# 唯一真相源：之前散落在 monitoring/run.py 的裸 env 读取收敛到此。
SPEND_ENV = "GEO_MONITOR_ALLOW_SPEND"


class SpendNotAuthorizedError(RuntimeError):
    """未授权花钱即试图真打付费引擎。独立异常类——与 require_ark 的『缺凭证』
    RuntimeError 精确区分（同时缺两者时先报花钱未授权，不泄露凭证细节）。"""


def spend_allowed() -> bool:
    """是否已授权花钱。严格 GEO_MONITOR_ALLOW_SPEND=='1'（fail-closed，不放宽 true/yes/带空格）。"""
    return os.environ.get(SPEND_ENV) == "1"


def require_spend() -> None:
    """真打付费引擎前的硬门控。未授权则 fail-closed 抛错，绝不静默花钱。

    注意：mock 路径绝不调用本函数（零成本跑通管道不该被门控）。
    """
    if not spend_allowed():
        raise SpendNotAuthorizedError(
            f"⛔ 拒绝花钱：未设 {SPEND_ENV}=1。\n"
            f"   真打付费引擎（豆包等）会产生费用，红线 §3 要求花钱前人审。\n"
            f"   • 零成本跑通管道：改用 mock 路径（`--mock-only` / mock 段）。\n"
            f"   • 确需真跑：显式 `export {SPEND_ENV}=1` 后重试。"
        )


def get_settings() -> Settings:
    # 函数内 import 化解 import 循环（category 模块不依赖 config）。
    from geo.category import active_profile

    prof = active_profile()
    return Settings(
        category_root=prof.root,
        evidence_dir=prof.root / "evidence",
        watchlist_path=prof.root / "config" / "watchlist.yaml",
    )
