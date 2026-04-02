from __future__ import annotations

import argparse
import sys

from backend.secrets.vault import set_secret


def main() -> int:
    parser = argparse.ArgumentParser(description="Store an exchange secret in the local encrypted vault.")
    parser.add_argument("name", help="Secret name")
    parser.add_argument("value", help="Secret value")
    parser.add_argument("--passphrase", help="Vault passphrase override", default=None)
    args = parser.parse_args()
    try:
        result = set_secret(args.name, args.value, args.passphrase)
    except Exception as exc:
        print(f"Failed to store secret: {exc}")
        return 1
    print("Vault updated.")
    print("Configured keys:", ", ".join(result["configured_keys"]) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
