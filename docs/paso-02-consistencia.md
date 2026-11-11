# Paso 2: persistencia y consistencia

Fecha: 2026-11-10 (America/Bogota). Tarea: T-011 (depende de T-010). Rama: `paso-02-consistencia`. Estado: implementado y probado localmente; **sin commit, sin revisión registrada y sin aceptación humana**.

## Hallazgos corregidos

| Hallazgo | Corrección | Prueba |
|---|---|---|
| El autoguardado cancelaba el temporizador al desmontar: escribir y cambiar de sección antes de 1,2 s perdía el cambio | `frontend/src/lib/saver.js`: guardado diferido, **serializado** (nunca dos PUT simultáneos) y que **guarda** al desmontar en lugar de cancelar. Registro global con `flushAll()` antes de exportar y de cerrar sesión, y aviso `beforeunload` si queda algo pendiente. Las secciones editables quedan montadas (se ocultan con `hidden`) para no descartar borradores. Tras cada guardado se actualiza la revisión en la referencia para que un guardado encadenado no provoque un 409 propio | `frontend/tests/saver.test.js` (5) y E2E «cambio conservado al cambiar de sección antes del autoguardado» |
| Eliminar un registro no eliminaba su copia Silver; `refresh_silver()` no retiraba copias antiguas | `lake.silver_sync_record()` se invoca al crear, modificar, verificar, adjuntar/eliminar soportes y eliminar. `refresh_silver()` retira huérfanas (`removed`). El objeto Silver eliminado queda `deleted: true` en el catálogo | `test_consistencia.py`: creación/actualización, eliminación, huérfanas, Gold sin eliminados, Silver refleja verificación y soporte |
| `build_gold()` aplicaba el umbral sobre registros | El umbral se aplica sobre **personas distintas** por celda; cada métrica guarda `value` (registros) y `personas` | `test_gold_umbral_por_personas_distintas_no_por_registros` (1 persona con 6 registros se suprime) |
| Cambiar `tipo_entidad` no invalidaba la verificación | `VERIFICATION_FIELDS` en `resume/service.py`: el cambio deja la entidad en `pending` sin `organization_id`; con soportes cargados responde 409 `soportes_existentes` sin modificar nada | 3 pruebas (invalida, otros cambios la conservan, 409 con soportes) |
| La idempotencia comparaba solo el archivo | Se compara la operación completa (archivo + tipo + registro). Además, un fallo de almacenamiento libera la clave para reintentar con la misma | 2 pruebas |
| `/api/health` respondía 200 con MongoDB caído | Responde 503 `{"status":"degraded","db":"error"}` | `test_health_devuelve_503_si_mongo_falla` |
| Pages podía publicar con pruebas fallidas | `pages.yml` ejecuta `quality.yml` (reutilizable con `workflow_call`) como primer job; `build` depende de él | Solo revisión de sintaxis: **no ejecutado en GitHub** |
| `render.yaml` no configuraba `ADMIN_TOKEN` | `generateValue: true` | No desplegado |
| La vigencia del harness solo comparaba `HEAD` | `tree()`: huella SHA-256 de HEAD + diff sin commit + archivos no versionados (excluye `harness/state.json` y evidencias). `fresh()`, `review` y `close` exigen la misma huella; `close` exige además árbol limpio | 3 pruebas nuevas en `test_harness.py` |

## Resultados reproducidos (Windows, MongoDB 8.2.6 local en un puerto y directorio de datos aparte)

| Comprobación | Resultado |
|---|---|
| Backend completo (`pytest`) | **104 aprobadas** (89 anteriores + 12 de consistencia + 3 del harness) |
| Frontend (`npm test`) | **13 aprobadas** (8 + 5 del guardador) |
| `npm run build` | Correcta |
| E2E Chromium (`scripts/local_checks.py e2e`, fuente simulada) | **15 comprobaciones aprobadas** |
| `harness.py validate` | Correcta |

El E2E se ajustó para localizar solo elementos visibles (`:visible`), porque ahora las secciones ocultas siguen montadas.

## Lo que este paso NO cierra

- Verificación educativa real (SNIES/SIET/DUE contra datos.gov.co) y canal laboral (RUES/SIGEP): pendiente, es el paso 3.
- Ejecución programada de Gold y de `cleanup_stale`: no existe todavía.
- Docker (pendiente desde el paso 1), Atlas, Supabase, Render y GitHub Actions: sin ejecutar.
- Al cambiar `tipo_entidad` con soportes, la interfaz muestra el error del servidor pero el formulario conserva el valor elegido hasta que el usuario lo revierta o elimine los soportes.
