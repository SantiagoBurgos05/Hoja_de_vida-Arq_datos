"""Configuración por variables de entorno. Sin secretos en el código."""
from __future__ import annotations
import os
from dataclasses import dataclass, field


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "si")


@dataclass
class Settings:
    mongo_uri: str = field(default_factory=lambda: os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017"))
    mongo_db: str = field(default_factory=lambda: os.getenv("MONGO_DB", "hoja_de_vida"))
    cors_origins: list[str] = field(default_factory=lambda: [o for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o])
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


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def set_settings(s: Settings | None) -> None:
    global _settings
    _settings = s
