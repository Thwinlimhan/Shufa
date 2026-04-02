from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.auth.service import require_role
from backend.ops.audit import record_audit_event
from backend.secrets.vault import delete_secret, get_secret, set_secret, vault_status

router = APIRouter()


@router.get("/status")
def status(user: dict = Depends(require_role("admin"))) -> dict:
    return vault_status()


@router.post("/secrets")
def put_secret(payload: dict, user: dict = Depends(require_role("admin"))) -> dict:
    try:
        result = set_secret(payload["name"], payload["value"], payload.get("passphrase"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    record_audit_event(
        event_type="vault.secret_set",
        entity_type="vault",
        entity_id=payload["name"],
        payload={"updated_by": user["display_name"]},
    )
    return result


@router.post("/secrets/delete")
def remove_secret(payload: dict, user: dict = Depends(require_role("admin"))) -> dict:
    try:
        result = delete_secret(payload["name"], payload.get("passphrase"))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    record_audit_event(
        event_type="vault.secret_deleted",
        entity_type="vault",
        entity_id=payload["name"],
        payload={"deleted_by": user["display_name"]},
    )
    return result


@router.get("/peek/{name}")
def peek_secret(name: str, user: dict = Depends(require_role("admin"))) -> dict:
    return {"name": name, "configured": bool(get_secret(name))}
