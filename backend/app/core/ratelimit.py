"""Límites de uso por ventana deslizante sobre MongoDB (colección `rate_events`, con TTL).

No es atómico: dos peticiones simultáneas pueden superar el límite en una unidad. Basta para frenar
abuso (registro masivo, consultas a fuentes externas, cargas) dentro del plan gratuito.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Request
from .config import get_settings
from .db import get_db


def client_ip(request: Request) -> str:
    """IP del cliente. Detrás de un proxy de confianza (Render) se usa el primer salto de X-Forwarded-For."""
    if get_settings().trust_proxy:
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd.strip():
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "?"


def enforce(bucket: str, subject: str, limit: tuple) -> None:
    """Registra un evento y responde 429 si `subject` ya alcanzó el máximo de eventos en la ventana."""
    max_events, window_s = limit
    now = datetime.now(timezone.utc)
    key = f"{bucket}|{subject}"
    db = get_db()
    if db.rate_events.count_documents({"key": key, "at": {"$gte": now - timedelta(seconds=window_s)}}) >= max_events:
        raise HTTPException(429, {"code": "limite_de_uso", "message": "Demasiadas solicitudes. Intente de nuevo más tarde.",
                                  "retry_after_s": window_s})
    db.rate_events.insert_one({"key": key, "at": now})
