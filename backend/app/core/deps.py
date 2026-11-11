from __future__ import annotations
from datetime import datetime, timezone
from bson import ObjectId
import hmac
from fastapi import Depends, Header, HTTPException
from .config import get_settings
from .db import get_db
from .security import token_hash


def current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "No autenticado")
    token = authorization[7:].strip()
    db = get_db()
    s = db.sessions.find_one({"token_hash": token_hash(token)})
    if not s or s["expires_at"] <= datetime.now(timezone.utc):
        raise HTTPException(401, "Sesión inválida o vencida")
    u = db.users.find_one({"_id": s["user_id"]})
    if not u:
        raise HTTPException(401, "Sesión inválida")
    return u


def oid(value: str) -> ObjectId:
    """ObjectId inválido => 404 (no revela formato)."""
    try:
        return ObjectId(value)
    except Exception:
        raise HTTPException(404, "No encontrado")


def audit(user_id, event: str, **data) -> None:
    get_db().audit_events.insert_one({"user_id": user_id, "event": event, "data": data, "at": datetime.now(timezone.utc)})


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    """Operaciones de administración: requieren ADMIN_TOKEN configurado (vacío = desactivadas)."""
    tok = get_settings().admin_token
    if not tok or not x_admin_token or not hmac.compare_digest(x_admin_token, tok):
        raise HTTPException(403, "No autorizado")


CurrentUser = Depends(current_user)
AdminOnly = Depends(require_admin)
