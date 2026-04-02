from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.auth.service import current_user, get_user_by_token, list_users

router = APIRouter()


@router.get("/session")
def session(user: dict = Depends(current_user)) -> dict:
    return user


@router.get("/users")
def users() -> list[dict]:
    return list_users()


@router.post("/login")
def login(payload: dict) -> dict:
    role = payload.get("role", "operator")
    user = next((item for item in list_users() if item["role"] == role), None)
    if user is None:
        raise HTTPException(status_code=404, detail="role_not_found")
    return user


@router.post("/token")
def token_session(payload: dict) -> dict:
    return get_user_by_token(payload.get("token"))
