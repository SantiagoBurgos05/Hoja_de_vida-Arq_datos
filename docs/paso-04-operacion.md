# Paso 4: operación del Data Lake y protección de recursos

Fecha: 2026-11-10 (America/Bogota). Tarea: T-013 (depende de T-012). Estado: implementado y probado localmente; **sin revisión registrada ni aceptación humana**. El workflow programado no se ha ejecutado en GitHub (no hay remoto).

## Mantenimiento

`POST /api/admin/maintenance` (cabecera `X-Admin-Token`) y `cd backend && python -m app.maintenance` ejecutan, en orden y de forma idempotente:

| Paso | Qué hace |
|---|---|
| `expire_stale_uploads` | Una carga en `uploading` con más de `STALE_UPLOAD_MINUTES` (60) pasa a `rejected`, se borra su objeto y se libera su clave de idempotencia |
| `retry_pending_deletes` | Completa los borrados que quedaron en `delete_pending` por un fallo de Storage: objeto, tombstone en Bronze, metadatos y estado del registro |
| `cleanup_stale` | Retención: elimina temporales y rechazados con más de 30 días |
| `reconcile_silver` | Reconstruye Silver de cada propietario y retira copias huérfanas |
| `build_gold` | Reconstruye Gold con el umbral por personas distintas |

Cada paso se ejecuta aunque otro falle. La respuesta es 200 si todos terminaron bien y 500 si alguno falló, con el error de cada paso; la ejecución queda en la colección `maintenance_runs` (`GET /api/admin/maintenance` lista las últimas).

**Programación sin costo:** `.github/workflows/maintenance.yml` lo invoca a diario (03:17 Bogotá) y a demanda. Necesita la variable `API_URL` y el secreto `ADMIN_TOKEN`; sin ellos termina con un aviso. Reintenta mientras Render despierta.

## Protección de recursos

- **Cuota:** `USER_STORAGE_QUOTA_MB` (25 MB por defecto) por usuario, contando soportes `uploading`, `ready` y `delete_pending`. Excederla responde 413 `cuota_excedida`; un duplicado o una repetición idempotente no cuentan. `GET /api/documents/usage` alimenta el texto «espacio usado X de Y» en la interfaz.
- **Límites de uso** (`core/ratelimit.py`, colección `rate_events` con TTL de 24 h): registro 10/h por IP, búsquedas + verificaciones de entidades 60 cada 10 min por usuario, cargas 30/h por usuario. Respuesta 429 `limite_de_uso`. Con `TRUST_PROXY=true` (Render) la IP sale del primer valor de `X-Forwarded-For`; sin ella esa cabecera se ignora para que no se pueda falsificar.
- El login reutiliza la misma función de IP.

## Resultados

| Comprobación | Resultado |
|---|---|
| Backend (`pytest`, MongoDB 8.2.6 local) | **125 aprobadas** (114 + 11 de `test_mantenimiento.py`) |
| Frontend: pruebas y compilación | 13 aprobadas; compilación correcta |
| E2E Chromium | 15 comprobaciones aprobadas |
| `harness.py validate` | Correcta (endpoints nuevos en `api.md` y `features.json`, RF10) |

## Límites declarados

- Los contadores de límites y la cuota no son atómicos: bajo concurrencia pueden excederse en una petición o un archivo.
- No hay límite global para el resto de rutas autenticadas.
- El workflow y las variables de Render no se han probado en vivo (paso 5).
