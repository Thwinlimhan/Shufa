from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _list_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    binance_base_url: str = os.getenv("BINANCE_BASE_URL", "https://fapi.binance.com")
    hyperliquid_base_url: str = os.getenv("HYPERLIQUID_BASE_URL", "https://api.hyperliquid.xyz")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-haiku")
    auth_viewer_token: str = os.getenv("AUTH_VIEWER_TOKEN", "viewer-token")
    auth_operator_token: str = os.getenv("AUTH_OPERATOR_TOKEN", "operator-token")
    auth_admin_token: str = os.getenv("AUTH_ADMIN_TOKEN", "admin-token")
    auth_cookie_name: str = os.getenv("AUTH_COOKIE_NAME", "workbench_token")
    auth_cookie_secure: bool = _bool_env("AUTH_COOKIE_SECURE", False)
    auth_cookie_max_age_seconds: int = int(os.getenv("AUTH_COOKIE_MAX_AGE_SECONDS", str(60 * 60 * 8)))
    binance_api_key: str = os.getenv("BINANCE_API_KEY", "")
    binance_api_secret: str = os.getenv("BINANCE_API_SECRET", "")
    hyperliquid_private_key: str = os.getenv("HYPERLIQUID_PRIVATE_KEY", "")
    hyperliquid_account_address: str = os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS", "")
    vault_passphrase: str = os.getenv("VAULT_PASSPHRASE", "")
    raw_data_root: Path = Path(os.getenv("RAW_DATA_ROOT", "./data/raw"))
    curated_db_path: Path = Path(os.getenv("CURATED_DB_PATH", "./data/curated/workbench.duckdb"))
    meta_db_path: Path = Path(os.getenv("META_DB_PATH", "./data/meta/workbench.db"))
    vault_file_path: Path = Path(os.getenv("VAULT_FILE_PATH", "./data/meta/secrets.vault"))
    app_log_path: Path = Path(os.getenv("APP_LOG_PATH", "./data/meta/workbench.log"))
    paper_initial_capital_usd: float = float(os.getenv("PAPER_INITIAL_CAPITAL_USD", "100000"))
    paper_fee_bps: float = float(os.getenv("PAPER_FEE_BPS", "4.0"))
    paper_slippage_bps: float = float(os.getenv("PAPER_SLIPPAGE_BPS", "3.0"))
    paper_trading_enabled: bool = _bool_env("PAPER_TRADING_ENABLED", True)
    paper_max_open_positions: int = int(os.getenv("PAPER_MAX_OPEN_POSITIONS", "4"))
    paper_max_gross_exposure_usd: float = float(os.getenv("PAPER_MAX_GROSS_EXPOSURE_USD", "40000"))
    paper_max_signal_correlation: float = float(os.getenv("PAPER_MAX_SIGNAL_CORRELATION", "0.92"))
    paper_daily_loss_limit_usd: float = float(os.getenv("PAPER_DAILY_LOSS_LIMIT_USD", "1500"))
    paper_day_reset_hour_utc: int = int(os.getenv("PAPER_DAY_RESET_HOUR_UTC", "0"))
    data_readiness_coverage_days: float = float(os.getenv("DATA_READINESS_COVERAGE_DAYS", "20"))
    paper_readiness_min_events: int = int(os.getenv("PAPER_READINESS_MIN_EVENTS", "10"))
    live_trading_enabled: bool = _bool_env("LIVE_TRADING_ENABLED", False)
    live_approval_mode: bool = _bool_env("LIVE_APPROVAL_MODE", True)
    live_network_enabled: bool = _bool_env("LIVE_NETWORK_ENABLED", False)
    scheduler_enabled: bool = _bool_env("SCHEDULER_ENABLED", False)
    worker_max_retries: int = int(os.getenv("WORKER_MAX_RETRIES", "3"))
    worker_retry_backoff_seconds: int = int(os.getenv("WORKER_RETRY_BACKOFF_SECONDS", "5"))
    worker_heartbeat_ttl_seconds: int = int(os.getenv("WORKER_HEARTBEAT_TTL_SECONDS", "30"))
    alerts_telegram_bot_token: str = os.getenv("ALERTS_TELEGRAM_BOT_TOKEN", "")
    alerts_telegram_chat_id: str = os.getenv("ALERTS_TELEGRAM_CHAT_ID", "")
    alerts_discord_webhook_url: str = os.getenv("ALERTS_DISCORD_WEBHOOK_URL", "")
    alerts_email_smtp_host: str = os.getenv("ALERTS_EMAIL_SMTP_HOST", "")
    alerts_email_smtp_port: int = int(os.getenv("ALERTS_EMAIL_SMTP_PORT", "587"))
    alerts_email_username: str = os.getenv("ALERTS_EMAIL_USERNAME", "")
    alerts_email_password: str = os.getenv("ALERTS_EMAIL_PASSWORD", "")
    alerts_email_from: str = os.getenv("ALERTS_EMAIL_FROM", "")
    alerts_email_to: str = os.getenv("ALERTS_EMAIL_TO", "")
    market_streams_enabled: bool = _bool_env("MARKET_STREAMS_ENABLED", False)
    cors_allow_origins: list[str] = field(
        default_factory=lambda: _list_env("CORS_ALLOW_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    )
    cors_allow_methods: list[str] = field(default_factory=lambda: _list_env("CORS_ALLOW_METHODS", "GET,POST,OPTIONS"))
    cors_allow_headers: list[str] = field(
        default_factory=lambda: _list_env("CORS_ALLOW_HEADERS", "Content-Type,X-Workbench-Token")
    )
    api_rate_limit_global_per_minute: int = int(os.getenv("API_RATE_LIMIT_GLOBAL_PER_MINUTE", "600"))
    api_rate_limit_auth_token_per_minute: int = int(os.getenv("API_RATE_LIMIT_AUTH_TOKEN_PER_MINUTE", "10"))
    api_rate_limit_ticket_approve_per_minute: int = int(os.getenv("API_RATE_LIMIT_TICKET_APPROVE_PER_MINUTE", "20"))


settings = Settings()
