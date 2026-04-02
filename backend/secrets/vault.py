from __future__ import annotations

import base64
import json
import os
from pathlib import Path

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    CRYPTOGRAPHY_AVAILABLE = True
except ModuleNotFoundError:
    Fernet = None
    hashes = None
    PBKDF2HMAC = None
    CRYPTOGRAPHY_AVAILABLE = False

from backend.core.config import settings

VAULT_KEYS = {
    "binance_api_key",
    "binance_api_secret",
    "hyperliquid_private_key",
    "hyperliquid_account_address",
}


def _require_cryptography() -> None:
    if not CRYPTOGRAPHY_AVAILABLE:
        raise RuntimeError("vault_dependency_missing")


def _vault_path() -> Path:
    path = settings.vault_file_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _resolve_passphrase(passphrase: str | None = None) -> str:
    resolved = passphrase or settings.vault_passphrase
    if not resolved:
        raise ValueError("vault_passphrase_required")
    return resolved


def _derive_fernet(passphrase: str, salt: bytes) -> Fernet:
    _require_cryptography()
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=390000)
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))
    return Fernet(key)


def _read_vault(passphrase: str | None = None) -> dict[str, str]:
    path = _vault_path()
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    salt = base64.b64decode(payload["salt"])
    fernet = _derive_fernet(_resolve_passphrase(passphrase), salt)
    decrypted = fernet.decrypt(payload["ciphertext"].encode("utf-8")).decode("utf-8")
    return json.loads(decrypted)


def _write_vault(data: dict[str, str], passphrase: str | None = None) -> None:
    path = _vault_path()
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    salt = base64.b64decode(existing["salt"]) if existing else os.urandom(16)
    fernet = _derive_fernet(_resolve_passphrase(passphrase), salt)
    ciphertext = fernet.encrypt(json.dumps(data).encode("utf-8")).decode("utf-8")
    path.write_text(
        json.dumps({"salt": base64.b64encode(salt).decode("utf-8"), "ciphertext": ciphertext}, indent=2),
        encoding="utf-8",
    )


def set_secret(name: str, value: str, passphrase: str | None = None) -> dict:
    _require_cryptography()
    if name not in VAULT_KEYS:
        raise ValueError("unsupported_secret_name")
    data = _read_vault(passphrase)
    data[name] = value
    _write_vault(data, passphrase)
    return vault_status(passphrase)


def delete_secret(name: str, passphrase: str | None = None) -> dict:
    _require_cryptography()
    data = _read_vault(passphrase)
    data.pop(name, None)
    _write_vault(data, passphrase)
    return vault_status(passphrase)


def get_secret(name: str, passphrase: str | None = None) -> str | None:
    try:
        data = _read_vault(passphrase)
    except (ValueError, RuntimeError):
        return None
    return data.get(name)


def secret_or_env(name: str) -> str | None:
    return get_secret(name) or getattr(settings, name, "")


def vault_status(passphrase: str | None = None) -> dict:
    path = _vault_path()
    data: dict[str, str] = {}
    unlocked = False
    dependency_error = None
    try:
        data = _read_vault(passphrase)
        unlocked = True
    except RuntimeError as exc:
        dependency_error = str(exc)
        unlocked = False
    except Exception:
        unlocked = False
    return {
        "path": str(path),
        "available": CRYPTOGRAPHY_AVAILABLE,
        "exists": path.exists(),
        "unlocked": unlocked,
        "configured_keys": sorted(data.keys()) if unlocked else [],
        "required_keys": sorted(VAULT_KEYS),
        "dependency_error": dependency_error,
    }
