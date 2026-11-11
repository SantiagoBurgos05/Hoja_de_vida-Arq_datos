from __future__ import annotations
from pymongo import MongoClient, ASCENDING
from pymongo.database import Database
from .config import get_settings
from .schemas_mongo import VALIDATORS

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        s = get_settings()
        _client = MongoClient(s.mongo_uri, maxPoolSize=10, serverSelectionTimeoutMS=5000, tz_aware=True)
    return _client


def get_db() -> Database:
    return get_client()[get_settings().mongo_db]


def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def init_db(db: Database | None = None) -> None:
    """Crea colecciones con validador e índices. Idempotente."""
    db = db if db is not None else get_db()
    existing = set(db.list_collection_names())
    for name, schema in VALIDATORS.items():
        opts = {"validator": {"$jsonSchema": schema}, "validationLevel": "strict", "validationAction": "error"}
        if name in existing:
            db.command("collMod", name, **opts)
        else:
            db.create_collection(name, **opts)

    db.users.create_index("email", unique=True)
    db.sessions.create_index("token_hash", unique=True)
    db.sessions.create_index("expires_at", expireAfterSeconds=0)            # TTL
    db.login_attempts.create_index("at", expireAfterSeconds=3600)           # TTL
    db.login_attempts.create_index("key")
    db.rate_events.create_index("at", expireAfterSeconds=86400)              # TTL: ventanas de hasta 24 h
    db.rate_events.create_index([("key", ASCENDING), ("at", ASCENDING)])
    db.maintenance_runs.create_index("started_at")
    db.resumes.create_index("user_id", unique=True)                         # 1 hoja de vida por usuario
    for c in ("education_records", "work_records"):
        db[c].create_index([("user_id", ASCENDING), ("resume_id", ASCENDING)])
    # Una organización oficial es única por (fuente, identificador oficial). No por nombre.
    db.organizations.create_index([("source", ASCENDING), ("official_id", ASCENDING)], unique=True)
    db.org_verifications.create_index([("user_id", ASCENDING), ("queried_at", ASCENDING)])
    db.documents.create_index([("user_id", ASCENDING), ("record_type", ASCENDING), ("record_id", ASCENDING)])
    # Idempotencia: misma clave del mismo usuario = misma operación.
    db.documents.create_index([("user_id", ASCENDING), ("idempotency_key", ASCENDING)], unique=True,
                              partialFilterExpression={"idempotency_key": {"$type": "string"}})
    # Control de duplicados: mismo contenido del mismo usuario en el mismo registro solo una vez (activos).
    db.documents.create_index([("user_id", ASCENDING), ("record_id", ASCENDING), ("sha256", ASCENDING)], unique=True,
                              partialFilterExpression={"document_status": {"$in": ["uploading", "ready"]}})
    db.lake_objects.create_index([("layer", ASCENDING), ("owner_id", ASCENDING), ("sha256", ASCENDING)])
    db.lake_objects.create_index("derived_from")
    db.silver_records.create_index([("owner_id", ASCENDING), ("kind", ASCENDING), ("source_id", ASCENDING)], unique=True)
    db.gold_metrics.create_index([("metric", ASCENDING), ("dimension", ASCENDING)])
    db.audit_events.create_index([("user_id", ASCENDING), ("at", ASCENDING)])
