from __future__ import annotations

import secrets
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


DEFAULTS = {
    "BINANCE_BASE_URL": "https://fapi.binance.com",
    "HYPERLIQUID_BASE_URL": "https://api.hyperliquid.xyz",
    "OPENROUTER_API_KEY": "",
    "OPENROUTER_MODEL": "anthropic/claude-3.5-haiku",
    "AUTH_VIEWER_TOKEN": "viewer-token",
    "AUTH_OPERATOR_TOKEN": "operator-token",
    "AUTH_ADMIN_TOKEN": "admin-token",
    "VAULT_PASSPHRASE": secrets.token_urlsafe(24),
    "VAULT_FILE_PATH": "./data/meta/secrets.vault",
    "RAW_DATA_ROOT": "./data/raw",
    "CURATED_DB_PATH": "./data/curated/workbench.duckdb",
    "META_DB_PATH": "./data/meta/workbench.db",
    "PAPER_INITIAL_CAPITAL_USD": "100000",
    "PAPER_SLIPPAGE_BPS": "3.0",
    "PAPER_TRADING_ENABLED": "true",
    "PAPER_MAX_OPEN_POSITIONS": "4",
    "PAPER_DAILY_LOSS_LIMIT_USD": "1500",
    "DATA_READINESS_COVERAGE_DAYS": "20",
    "PAPER_READINESS_MIN_EVENTS": "10",
    "LIVE_TRADING_ENABLED": "false",
    "LIVE_APPROVAL_MODE": "true",
    "LIVE_NETWORK_ENABLED": "false",
    "BINANCE_API_KEY": "",
    "BINANCE_API_SECRET": "",
    "HYPERLIQUID_PRIVATE_KEY": "",
    "HYPERLIQUID_ACCOUNT_ADDRESS": "",
    "SCHEDULER_ENABLED": "false",
}


def main() -> None:
    if ENV_PATH.exists():
        print(f".env already exists at {ENV_PATH}")
        return
    content = "\n".join(f"{key}={value}" for key, value in DEFAULTS.items()) + "\n"
    ENV_PATH.write_text(content, encoding="utf-8")
    print(f"Created secure runtime .env at {ENV_PATH}")
    print("LIVE_TRADING_ENABLED=false and LIVE_NETWORK_ENABLED=false were left off for safety.")


if __name__ == "__main__":
    main()
