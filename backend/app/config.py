"""Environment-driven configuration. No secrets in source — everything via env vars.

Provider blocks (timeout / retry / rate limit / cache TTL) are defined here so the
resilient clients built in Phase 1 read their policy from one place (HL5).
"""

from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderConfig(BaseModel):
    """Per-upstream resilience policy (HL5). Verify live rate limits against provider docs."""

    name: str
    base_url: str
    api_key_env: str | None = None
    timeout_s: float = 5.0
    retry_max: int = 3
    backoff_base_s: float = 0.5
    rate_limit_per_hour: int | None = None
    cache_ttl_s: int = 900


# Static upstream catalog. Keys are read from the env var named by ``api_key_env``.
PROVIDERS: dict[str, ProviderConfig] = {
    "openaq": ProviderConfig(
        name="OpenAQ",
        base_url="https://api.openaq.org/v3",
        api_key_env="OPENAQ_API_KEY",
        rate_limit_per_hour=None,
        cache_ttl_s=900,
    ),
    "airnow": ProviderConfig(
        name="AirNow",
        base_url="https://www.airnowapi.org",
        api_key_env="AIRNOW_API_KEY",
        rate_limit_per_hour=500,  # historically strict — confirm in docs.
        cache_ttl_s=1800,
    ),
    "open-meteo": ProviderConfig(
        name="Open-Meteo",
        base_url="https://api.open-meteo.com/v1",
        api_key_env=None,  # no key required
        rate_limit_per_hour=None,
        cache_ttl_s=900,
    ),
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    app_env: str = "dev"
    log_level: str = "INFO"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # Hard-limit-derived knobs.
    stale_threshold_hours: int = 3  # HL1
    max_horizon_hours: int = 24  # plan.md Phase 5: forecast 1->24h
    forecast_latency_budget_ms: int = 800  # HL5 (p95 from cache)
    request_timeout_s: float = 5.0  # HL5
    retry_max: int = 3  # HL5

    # Secrets — supplied only via env / .env (gitignored).
    openaq_api_key: str | None = None
    airnow_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
