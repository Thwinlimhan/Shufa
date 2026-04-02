from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    binance_base_url: str = os.getenv("BINANCE_BASE_URL", "https://fapi.binance.com")
    hyperliquid_base_url: str = os.getenv("HYPERLIQUID_BASE_URL", "https://api.hyperliquid.xyz")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-haiku")
    auth_viewer_token: str = os.getenv("AUTH_VIEWER_TOKEN", "viewer-token")
    auth_operator_token: str = os.getenv("AUTH_OPERATOR_TOKEN", "operator-token")
    auth_admin_token: str = os.getenv("AUTH_ADMIN_TOKEN", "admin-token")
    binance_api_key: str = os.getenv("BINANCE_API_KEY", "")
    binance_api_secret: str = os.getenv("BINANCE_API_SECRET", "")
    hyperliquid_private_key: str = os.getenv("HYPERLIQUID_PRIVATE_KEY", "")
    hyperliquid_account_address: str = os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS", "")
    vault_passphrase: str = os.getenv("VAULT_PASSPHRASE", "")
    raw_data_root: Path = Path(os.getenv("RAW_DATA_ROOT", "./data/raw"))
    curated_db_path: Path = Path(os.getenv("CURATED_DB_PATH", "./data/curated/workbench.duckdb"))
    meta_db_path: Path = Path(os.getenv("META_DB_PATH", "./data/meta/workbench.db"))
    vault_file_path: Path = Path(os.getenv("VAULT_FILE_PATH", "./data/meta/secrets.vault"))
    paper_initial_capital_usd: float = float(os.getenv("PAPER_INITIAL_CAPITAL_USD", "100000"))
    paper_slippage_bps: float = float(os.getenv("PAPER_SLIPPAGE_BPS", "3.0"))
    paper_trading_enabled: bool = _bool_env("PAPER_TRADING_ENABLED", True)
    paper_max_open_positions: int = int(os.getenv("PAPER_MAX_OPEN_POSITIONS", "4"))
    paper_daily_loss_limit_usd: float = float(os.getenv("PAPER_DAILY_LOSS_LIMIT_USD", "1500"))
    data_readiness_coverage_days: float = float(os.getenv("DATA_READINESS_COVERAGE_DAYS", "20"))
    paper_readiness_min_events: int = int(os.getenv("PAPER_READINESS_MIN_EVENTS", "10"))
    live_trading_enabled: bool = _bool_env("LIVE_TRADING_ENABLED", False)
    live_approval_mode: bool = _bool_env("LIVE_APPROVAL_MODE", True)
    live_network_enabled: bool = _bool_env("LIVE_NETWORK_ENABLED", False)
    scheduler_enabled: bool = _bool_env("SCHEDULER_ENABLED", False)


settings = Settings()
