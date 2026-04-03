from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, Request

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


def list_users(include_tokens: bool = False) -> list[dict]:
    bootstrap_users()
    rows = fetch_all("SELECT user_id, display_name, role, token, created_at FROM app_users ORDER BY created_at", [])
    users = [dict(row) for row in rows]
    if include_tokens:
        return users
    for user in users:
        user.pop("token", None)
    return users


def public_user(user: dict) -> dict:
    return {
        "user_id": user["user_id"],
        "display_name": user["display_name"],
        "role": user["role"],
        "created_at": user["created_at"],
    }


def get_user_by_token(token: str | None) -> dict:
    bootstrap_users()
    if not token:
        raise HTTPException(status_code=401, detail="Missing auth token")
    row = fetch_one("SELECT user_id, display_name, role, token, created_at FROM app_users WHERE token=?", [token])
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid auth token")
    return dict(row)


def current_user(
    request: Request,
    x_workbench_token: str | None = Header(default=None),
) -> dict:
    auth_cookie = request.cookies.get(settings.auth_cookie_name)
    token = x_workbench_token or auth_cookie
    return get_user_by_token(token)


def require_role(min_role: str):
    def dependency(user: dict = Depends(current_user)) -> dict:
        current_priority = ROLE_PRIORITY.get(user["role"], 0)
        needed = ROLE_PRIORITY.get(min_role, 999)
        if current_priority < needed:
            raise HTTPException(status_code=403, detail=f"{min_role}_role_required")
        return user

    return dependency
