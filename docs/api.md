# API (generada y verificada por `harness.py validate`)

Todas las rutas, salvo `/api/health`, `/api/auth/register` y `/api/auth/login`, exigen `Authorization: Bearer <token>`.
Errores: 401 sin sesión, 404 para recursos ajenos o inexistentes, 409 conflicto de revisión (`revision_obsoleta`; `current` trae la versión del servidor), 409 `soportes_existentes` al cambiar `tipo_entidad` de una experiencia con soportes, 409 `idempotency_key_reutilizada` si la clave ya se usó para otro archivo u otro registro, 413/415/422 validación de archivos, 429 límite de intentos, 502 fallo de almacenamiento, 503 en `/api/health` si MongoDB no responde.

Notas de comportamiento:
- `PUT /api/work/{rid}`: cambiar `tipo_entidad` (pública ↔ privada) invalida la verificación previa (`organization_status = pending`, `organization_id = null`); con soportes cargados responde 409 y no cambia nada.
- Crear, modificar, verificar, adjuntar/eliminar soportes y eliminar registros sincroniza Silver en el mismo momento. `POST /api/lake/refresh-silver` reconstruye y retira copias huérfanas (`removed`).
- `POST /api/admin/maintenance` y `GET /api/admin/maintenance` exigen `X-Admin-Token` (= `ADMIN_TOKEN`; vacío ⇒ 403). El POST expira cargas interrumpidas, completa borrados pendientes, aplica la retención, concilia Silver y reconstruye Gold; responde 500 si algún paso falló (los demás se ejecutan igual) y deja registro en `maintenance_runs`. Misma operación por consola: `cd backend && python -m app.maintenance`.
- Cuota: `POST /api/documents` responde 413 `cuota_excedida` si el usuario superaría `USER_STORAGE_QUOTA_MB` (25 MB por defecto). `GET /api/documents/usage` informa `used_bytes`, `quota_bytes` y `available_bytes`.
- Límites de uso (429 `limite_de_uso`): registro 10/h por IP; búsquedas + verificaciones de entidades 60 cada 10 min por usuario; cargas 30/h por usuario. Con `TRUST_PROXY=true` la IP sale de `X-Forwarded-For` contada desde la **derecha** (`TRUSTED_PROXY_HOPS`, 1 por defecto): los valores de la izquierda los escribe el cliente y no se usan.
- `GET /api/lake/gold`: cada celda informa `value` (registros), `personas` (personas distintas) y `k`; solo se publican celdas con `personas ≥ k`.

| Método y ruta | Descripción |
|---|---|
| `GET /api/admin/maintenance` | Maintenance runs (admin) |
| `POST /api/admin/maintenance` | Maintenance (admin) |
| `POST /api/auth/login` | Login |
| `POST /api/auth/logout` | Logout |
| `GET /api/auth/me` | Me |
| `POST /api/auth/register` | Register |
| `GET /api/documents` | List documents |
| `GET /api/documents/usage` | Usage |
| `POST /api/documents` | Upload |
| `DELETE /api/documents/{doc_id}` | Delete |
| `GET /api/documents/{doc_id}/download` | Download |
| `GET /api/education` | List education |
| `POST /api/education` | Create education |
| `DELETE /api/education/{rid}` | Delete education |
| `PUT /api/education/{rid}` | Update education |
| `GET /api/export/pdf` | Pdf |
| `GET /api/export/preview` | Preview |
| `GET /api/health` | Health |
| `POST /api/lake/build-gold` | Build gold |
| `GET /api/lake/catalog` | Catalog |
| `GET /api/lake/gold` | Gold |
| `GET /api/lake/lineage/{object_id}` | Lineage |
| `POST /api/lake/refresh-silver` | Refresh |
| `POST /api/organizations/search` | Search |
| `POST /api/organizations/verify` | Verify |
| `GET /api/organizations/{org_id}` | Get org |
| `GET /api/resume` | Get resume |
| `PUT /api/resume` | Put resume |
| `GET /api/resume/experience-summary` | Experience summary |
| `GET /api/work` | List work |
| `POST /api/work` | Create work |
| `DELETE /api/work/{rid}` | Delete work |
| `PUT /api/work/{rid}` | Update work |
