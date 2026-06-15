"""Runtime config. Secrets come from .env / env vars only (红线 §7)."""
from __future__ import annotations

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

    # ── 路径 ──
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


def get_settings() -> Settings:
    return Settings()
