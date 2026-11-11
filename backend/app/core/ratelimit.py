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
    """IP del cliente para límites de uso y bloqueo de login.

    Sin proxy de confianza se usa la IP de la conexión. Con `TRUST_PROXY=true` (Render) se usa X-Forwarded-For
    contando desde la DERECHA: cada proxy agrega la IP que lo contactó al final, mientras que los valores de la
    izquierda los escribe el propio cliente y son falsificables. `TRUSTED_PROXY_HOPS` es cuántos proxies de
    confianza agregan valores (1 = el último valor es la IP real que vio el proxy de Render)."""
    s = get_settings()
    peer = request.client.host if request.client else "?"
    if not s.trust_proxy:
        return peer
    hops = [h.strip() for h in request.headers.get("x-forwarded-for", "").split(",") if h.strip()]
    if not hops:
        return peer
    return hops[-min(max(s.trusted_proxy_hops, 1), len(hops))]


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
