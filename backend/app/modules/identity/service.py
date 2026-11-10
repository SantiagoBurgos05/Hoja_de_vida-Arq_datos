from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pymongo.errors import DuplicateKeyError
from ...core.config import get_settings
from ...core.db import get_db
from ...core.errors import bad
from ...core.security import hash_password, verify_password, new_token, token_hash
from fastapi import HTTPException


def _now():
    return datetime.now(timezone.utc)


def register(email: str, password: str) -> dict:
    db = get_db()
    email = email.strip().lower()
    try:
        r = db.users.insert_one({"email": email, "password_hash": hash_password(password), "created_at": _now()})
    except DuplicateKeyError:
        # Mensaje genérico: no confirma si el correo existe.
        raise bad("registro_no_disponible", "No fue posible completar el registro con esos datos.", 409)
    return {"id": str(r.inserted_id), "email": email}


def _blocked(key: str) -> bool:
    s = get_settings()
    since = _now() - timedelta(minutes=s.login_window_minutes)
    return get_db().login_attempts.count_documents({"key": key, "at": {"$gte": since}}) >= s.login_max_attempts


def login(email: str, password: str, ip: str) -> dict:
    db = get_db()
    email = email.strip().lower()
    key = f"{email}|{ip}"
    if _blocked(key):
        raise HTTPException(429, "Demasiados intentos. Intente más tarde.")
    u = db.users.find_one({"email": email})
    ok = bool(u) and verify_password(u["password_hash"], password)
    if not ok:
        db.login_attempts.insert_one({"key": key, "at": _now()})
        raise HTTPException(401, "Credenciales inválidas")
    token = new_token()
    exp = _now() + timedelta(hours=get_settings().session_ttl_hours)
    db.sessions.insert_one({"user_id": u["_id"], "token_hash": token_hash(token), "expires_at": exp, "created_at": _now()})
    return {"token": token, "expires_at": exp.isoformat(), "user": {"id": str(u["_id"]), "email": u["email"]}}


def logout(token: str) -> None:
    get_db().sessions.delete_one({"token_hash": token_hash(token)})
