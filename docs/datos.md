# Modelo de datos (MongoDB)

Validación en dos capas: Pydantic en la API y `$jsonSchema` (`validationAction: error`) en la base (`backend/app/core/schemas_mongo.py`).

| Colección | Referencias | Índices |
|---|---|---|
| `users` | — | único `email` |
| `sessions` | `user_id` | único `token_hash` (solo hash), TTL `expires_at` |
| `login_attempts` | — | `key`, TTL 1 h |
| `resumes` | `user_id` | único `user_id` (1 hoja de vida por usuario); `revision` |
| `education_records`, `work_records` | `user_id`, `resume_id`, `organization_id?` | `(user_id, resume_id)` |
| `organizations` | evidencia → `lake_objects` | **único `(source, official_id)`** |
| `org_verifications` | `user_id`, `organization_id?` | `(user_id, queried_at)` |
| `documents` | `user_id`, `record_type+record_id`, `organization_id`, `lake_object_id` | único parcial `(user_id, idempotency_key)`; único parcial `(user_id, record_id, sha256)` en `uploading/ready` |
| `lake_objects` | `derived_from[]` | `(layer, owner_id, sha256)`, `derived_from` |
| `silver_records` | `lake_object_id` | único `(owner_id, kind, source_id)` |
| `gold_metrics` | `run_id` | `(metric, dimension)` |
| `audit_events` | `user_id` | `(user_id, at)` |

Autorización por propietario: toda consulta incluye `user_id` del token; un recurso ajeno responde **404**.
Archivos: bytes en Storage privado (clave `bronze/<user>/certificates/<doc_id>.<ext>`, sin nombre del usuario); en Mongo solo metadatos + `sha256`.
Fechas de formulario en ISO `YYYY-MM-DD` (texto); marcas de tiempo en `Date` UTC.
