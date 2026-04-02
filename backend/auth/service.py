from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException

from backend.core.config import settings
from backend.data.storage import fetch_all, fetch_one, save_json_record

ROLE_PRIORITY = {"viewer": 1, "operator": 2, "admin": 3}


def bootstrap_users() -> None:
    defaults = [
        ("viewer", "Viewer", settings.auth_viewer_token),
        ("operator", "Operator", settings.auth_operator_token),
        ("admin", "Admin", settings.auth_admin_token),
    ]
    created_at = datetime.now(timezone.utc).isoformat()
    for role, display_name, token in defaults:
        if not token:
            continue
        existing = fetch_one("SELECT user_id FROM app_users WHERE token=?", [token])
        if existing is None:
            save_json_record(
                "app_users",
                {
                    "user_id": role,
                    "display_name": display_name,
                    "role": role,
                    "token": token,
                    "created_at": created_at,
                },
                "user_id",
            )


def list_users() -> list[dict]:
    bootstrap_users()
    rows = fetch_all("SELECT user_id, display_name, role, token, created_at FROM app_users ORDER BY created_at")
    return [dict(row) for row in rows]


def get_user_by_token(token: str | None) -> dict:
    bootstrap_users()
    resolved = token or settings.auth_operator_token
    row = fetch_one("SELECT user_id, display_name, role, token, created_at FROM app_users WHERE token=?", [resolved])
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid auth token")
    return dict(row)


def current_user(x_workbench_token: str | None = Header(default=None)) -> dict:
    return get_user_by_token(x_workbench_token)


def require_role(min_role: str):
    def dependency(user: dict = Depends(current_user)) -> dict:
        current_priority = ROLE_PRIORITY.get(user["role"], 0)
        needed = ROLE_PRIORITY.get(min_role, 999)
        if current_priority < needed:
            raise HTTPException(status_code=403, detail=f"{min_role}_role_required")
        return user

    return dependency
