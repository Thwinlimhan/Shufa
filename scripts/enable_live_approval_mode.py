from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def main() -> None:
    if not ENV_PATH.exists():
        raise SystemExit(".env not found. Run scripts/bootstrap_secure_runtime.py first.")
    text = ENV_PATH.read_text(encoding="utf-8")
    replacements = {
        "LIVE_TRADING_ENABLED=false": "LIVE_TRADING_ENABLED=true",
        "LIVE_APPROVAL_MODE=true": "LIVE_APPROVAL_MODE=true",
        "LIVE_NETWORK_ENABLED=false": "LIVE_NETWORK_ENABLED=false",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    ENV_PATH.write_text(text, encoding="utf-8")
    print("Live approval mode enabled in .env with network execution still disabled.")


if __name__ == "__main__":
    main()
