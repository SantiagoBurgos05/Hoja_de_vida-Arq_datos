"""Configuración por variables de entorno. Sin secretos en el código."""
from __future__ import annotations
import os
from dataclasses import dataclass, field


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "si")


def _origins(raw: str) -> list[str]:
    """Orígenes CORS normalizados como los envía el navegador: esquema y host en minúsculas, sin `/` final.
    (`https://Usuario.github.io/` -> `https://usuario.github.io`; una ruta como `/repo` se descarta.)"""
    out = []
    for o in raw.split(","):
        o = o.strip()
        if not o:
            continue
        scheme, sep, rest = o.partition("://")
        host = rest.split("/", 1)[0] if sep else o
        out.append(f"{scheme.lower()}://{host.lower()}" if sep else o.lower())
    return out


@dataclass
class Settings:
    mongo_uri: str = field(default_factory=lambda: os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017"))
    mongo_db: str = field(default_factory=lambda: os.getenv("MONGO_DB", "hoja_de_vida"))
    cors_origins: list[str] = field(default_factory=lambda: _origins(os.getenv("CORS_ORIGINS", "http://localhost:5173")))
    session_ttl_hours: int = field(default_factory=lambda: int(os.getenv("SESSION_TTL_HOURS", "168")))
    max_upload_bytes: int = 5 * 1024 * 1024
    login_max_attempts: int = field(default_factory=lambda: int(os.getenv("LOGIN_MAX_ATTEMPTS", "5")))
    login_window_minutes: int = field(default_factory=lambda: int(os.getenv("LOGIN_WINDOW_MINUTES", "15")))
    storage_backend: str = field(default_factory=lambda: os.getenv("STORAGE_BACKEND", "local"))  # local | supabase
    local_storage_dir: str = field(default_factory=lambda: os.getenv("LOCAL_STORAGE_DIR", "./.storage"))
    supabase_url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    supabase_service_key: str = field(default_factory=lambda: os.getenv("SUPABASE_SERVICE_KEY", ""))
    supabase_bucket: str = field(default_factory=lambda: os.getenv("SUPABASE_BUCKET", "certificados"))
    allowed_connector_hosts: list[str] = field(default_factory=lambda: [h for h in os.getenv("ALLOWED_CONNECTOR_HOSTS", "www.datos.gov.co").split(",") if h])
    socrata_url_template: str = field(default_factory=lambda: os.getenv("SOCRATA_URL_TEMPLATE", "https://www.datos.gov.co/resource/{dataset}.json"))
    connector_timeout_s: float = float(os.getenv("CONNECTOR_TIMEOUT_S", "8"))
    connector_max_bytes: int = 1_000_000
    admin_token: str = field(default_factory=lambda: os.getenv("ADMIN_TOKEN", ""))
    temp_retention_days: int = 30
    gold_k_anonymity: int = 5
    # Protección de recursos (plan gratuito: Supabase 1 GB, Atlas 0,5 GB)
    user_storage_quota_bytes: int = field(default_factory=lambda: int(float(os.getenv("USER_STORAGE_QUOTA_MB", "25")) * 1024 * 1024))
    stale_upload_minutes: int = field(default_factory=lambda: int(os.getenv("STALE_UPLOAD_MINUTES", "60")))
    trust_proxy: bool = field(default_factory=lambda: _bool("TRUST_PROXY", False))   # Render: X-Forwarded-For
    # Límites de uso: (máximo de eventos, ventana en segundos)
    rate_register: tuple = (10, 3600)      # registros por IP
    rate_lookup: tuple = (60, 600)         # búsquedas + verificaciones por usuario (consultan fuentes externas)
    rate_upload: tuple = (30, 3600)        # cargas por usuario


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def set_settings(s: Settings | None) -> None:
    global _settings
    _settings = s
