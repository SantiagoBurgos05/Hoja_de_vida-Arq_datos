"""Esquemas $jsonSchema de MongoDB (segunda barrera; la primera es Pydantic).

Estados controlados:
  organization_status: pending | verified | not_found | error
  record_status:       draft | declared | supported
  document_status:     uploading | ready | rejected | delete_pending
  authenticity:        not_validated   (único valor posible: el sistema no autentica certificados)
"""
ORG_STATUS = ["pending", "verified", "not_found", "error"]
RECORD_STATUS = ["draft", "declared", "supported"]
DOC_STATUS = ["uploading", "ready", "rejected", "delete_pending"]
SOURCES = ["snies", "siet", "due", "rues", "sigep"]
LAYERS = ["bronze", "silver", "gold"]

VALIDATORS: dict[str, dict] = {
    "users": {
        "bsonType": "object",
        "required": ["email", "password_hash", "created_at"],
        "properties": {
            "email": {"bsonType": "string"},
            "password_hash": {"bsonType": "string"},
            "created_at": {"bsonType": "date"},
        },
    },
    "sessions": {
        "bsonType": "object",
        "required": ["user_id", "token_hash", "expires_at"],
        "properties": {"token_hash": {"bsonType": "string"}, "expires_at": {"bsonType": "date"}},
    },
    "resumes": {
        "bsonType": "object",
        "required": ["user_id", "revision", "personal", "education_basic", "languages"],
        "properties": {
            "revision": {"bsonType": ["int", "long"], "minimum": 0},
            "personal": {"bsonType": "object"},
            "education_basic": {"bsonType": "object"},
            "languages": {"bsonType": "array"},
        },
    },
    "education_records": {
        "bsonType": "object",
        "required": ["user_id", "resume_id", "record_status", "organization_status"],
        "properties": {
            "record_status": {"enum": RECORD_STATUS},
            "organization_status": {"enum": ORG_STATUS},
        },
    },
    "work_records": {
        "bsonType": "object",
        "required": ["user_id", "resume_id", "record_status", "organization_status"],
        "properties": {
            "record_status": {"enum": RECORD_STATUS},
            "organization_status": {"enum": ORG_STATUS},
        },
    },
    "organizations": {
        "bsonType": "object",
        "required": ["source", "official_id", "name", "status", "verified_at"],
        "properties": {"source": {"enum": SOURCES}, "status": {"enum": ["verified"]}},
    },
    "org_verifications": {
        "bsonType": "object",
        "required": ["user_id", "source", "official_id", "organization_status", "queried_at"],
        "properties": {"source": {"enum": SOURCES}, "organization_status": {"enum": ORG_STATUS}},
    },
    "documents": {
        "bsonType": "object",
        "required": ["user_id", "record_type", "record_id", "document_status", "authenticity", "sha256", "size"],
        "properties": {
            "document_status": {"enum": DOC_STATUS},
            "authenticity": {"enum": ["not_validated"]},
            "size": {"bsonType": ["int", "long"], "minimum": 0, "maximum": 5 * 1024 * 1024},
        },
    },
    "lake_objects": {
        "bsonType": "object",
        "required": ["layer", "kind", "created_at"],
        "properties": {"layer": {"enum": LAYERS}},
    },
    "silver_records": {"bsonType": "object", "required": ["owner_id", "kind", "data"]},
    "gold_metrics": {
        "bsonType": "object",
        "required": ["metric", "dimension", "value", "computed_at"],
        "properties": {"value": {"bsonType": ["int", "long"]}},
    },
    "audit_events": {"bsonType": "object", "required": ["event", "at"]},
    "login_attempts": {"bsonType": "object", "required": ["key", "at"]},
    "rate_events": {"bsonType": "object", "required": ["key", "at"]},
    "maintenance_runs": {"bsonType": "object", "required": ["started_at", "trigger", "ok"]},
}
