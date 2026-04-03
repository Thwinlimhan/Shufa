from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from backend.api.rate_limit import enforce_rate_limit
from backend.api.schemas import LogoutResponse, UserPublicResponse
from backend.auth.service import current_user, get_user_by_token, list_users, public_user, require_role
from backend.core.config import settings

router = APIRouter()


@router.get("/session", response_model=UserPublicResponse, summary="Current authenticated user")
def session(user: dict = Depends(current_user)) -> dict:
    return public_user(user)


@router.get("/users", response_model=list[UserPublicResponse], summary="List configured users")
def users(user: dict = Depends(require_role("admin"))) -> list[dict]:
    return list_users()


@router.post(
    "/login",
    response_model=UserPublicResponse,
    summary="Authenticate by role",
    description="Sets a secure HTTP-only auth cookie and returns the user profile.",
)
def login(payload: dict, response: Response) -> dict:
    role = payload.get("role", "operator")
    user = next((item for item in list_users(include_tokens=True) if item["role"] == role), None)
    if user is None:
        raise HTTPException(status_code=404, detail="role_not_found")
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=user["token"],
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.auth_cookie_max_age_seconds,
    )
    return public_user(user)


@router.post(
    "/token",
    response_model=UserPublicResponse,
    summary="Authenticate by token",
    description="Validates a token and sets an HTTP-only auth cookie.",
)
def token_session(payload: dict, request: Request, response: Response) -> dict:
    enforce_rate_limit(
        request,
        bucket="auth_token",
        limit=settings.api_rate_limit_auth_token_per_minute,
        window_seconds=60,
    )
    user = get_user_by_token(payload.get("token"))
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=user["token"],
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.auth_cookie_max_age_seconds,
    )
    return public_user(user)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Clear auth session",
    description="Clears the HTTP-only auth cookie.",
)
def logout(response: Response) -> dict:
    response.delete_cookie(key=settings.auth_cookie_name)
    return {"ok": True}
