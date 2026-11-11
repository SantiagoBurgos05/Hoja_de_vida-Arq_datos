# Estado real del proyecto (2026-11-10)

Fuente de verdad: lo que NO está en «Probado» no debe presentarse como hecho.

## Revisión actual: paso 2 (2026-11-10, Windows, rama `paso-02-consistencia`)

- Corregidos: pérdida de cambios al navegar antes del autoguardado, guardados concurrentes, Silver desincronizado al eliminar, umbral Gold por personas distintas, invalidación de verificación al cambiar `tipo_entidad`, idempotencia por operación completa, `/api/health` 503, Pages condicionado a `quality`, `ADMIN_TOKEN` en `render.yaml`, vigencia del harness por huella del contenido.
- Backend: **104 pruebas aprobadas** contra MongoDB 8.2.6 real. Frontend: **13 aprobadas** y compilación correcta. E2E Chromium: **15 comprobaciones aprobadas** (fuente **simulada**). `harness.py validate`: correcto.
- **Sin commit, sin revisión y sin aceptación humana** (T-011). Workflows y `render.yaml` solo modificados, no ejecutados. Detalle: [paso-02-consistencia.md](paso-02-consistencia.md).

## Revisión anterior: paso 1 (2026-11-10, Windows)

- Backend: **89 pruebas aprobadas** contra MongoDB **8.2.6 real**, con una instancia y datos sintéticos separados.
- Frontend: **8 pruebas aprobadas** y compilación correcta.
- Recorrido Chromium: **14 comprobaciones aprobadas**, incluida recuperación del certificado en otra sesión y exportación. Fuente educativa **simulada**.
- `harness.py validate` y `docker compose config --quiet`: correctos.
- Se corrigieron dependencias de pruebas ausentes y ejecución de npm desde el harness en Windows; se preparó el directorio de almacenamiento en la imagen y comprobaciones locales repetibles.
- **Paso 1 sin cerrar**: construcción y ejecución Docker pendientes por acceso denegado al motor desde esta sesión. Cambios sin commit; sin aceptación humana. No se ha iniciado el paso 2.

Detalle, límites y comandos: [paso-01-local.md](paso-01-local.md). Los resultados siguientes son históricos y no se presentan como mediciones nuevas.

## Resultados históricos registrados (entorno anterior)
| Qué | Cómo | Resultado |
|---|---|---|
| Backend: identidad, persistencia entre sesiones, 409 por revisión (incl. 8 guardados concurrentes), aislamiento entre usuarios, estados no falsificables, verificación de entidades (exacta por ID, error/ambiguo/no encontrado sin conceder, host fuera de lista blanca), soportes (validación de tipo/tamaño, idempotencia, concurrencia, fallo y truncado de almacenamiento, integridad, borrado coordinado y pendiente, retención), data lake (catálogo, linaje, Silver sin PII, Gold k≥5), validadores e índices de Mongo, exportación PDF (3 páginas, plantilla intacta, firma/RR.HH. en blanco, casillas, repetición de página 2) | `cd backend && pytest` contra **MongoDB 7.0.34 real** y almacenamiento local | **87 pruebas OK** (incluye 6 del harness; cobertura ≈ 94 %) |
| Frontend: utilidades y cliente API | `cd frontend && npm test` | **8 OK** |
| Frontend: compilación | `npm run build` | OK |
| Flujo completo en navegador real (Chromium): registro, autoguardado, recarga, nueva sesión, verificación, certificado, recuperación idéntica en otro navegador, RUES deshabilitado, tiempo total, exportación PDF, aislamiento, sin errores de consola | `python tests_e2e/e2e.py` (backend + Mongo reales + **fuente de entidades simulada** local) | **14 comprobaciones OK** |
| Coherencia documentación–código (endpoints, tareas, dependencias, sin campos de firma/RR.HH.) | `python scripts/harness.py validate` | OK |
| Sintaxis de `docker-compose.yml`, `render.yaml`, workflows | YAML + `docker compose config` | OK (solo sintaxis) |
| Revisión visual del PDF generado contra la plantilla | Renderizado y comparación de las 3 páginas | Alineado |

## Implementado pero NO probado en vivo
- **Consultas a fuentes oficiales** (SNIES `n5yy-8nav`, SIET `gpje-sixt`, establecimientos `cfw5-qzt5`): el entorno no pudo acceder a datos.gov.co. Los **nombres de columna son supuestos** (ver `docs/fuentes.md`). Probado solo con respuestas simuladas, incluida una prueba HTTP real contra un servidor simulado local.
- **Supabase Storage** (`SupabaseStorage`): escrito según la API REST documentada; sin proyecto real para probarlo.
- **MongoDB Atlas**: no probado; la validación `$jsonSchema` en M0 no se confirmó. Se prueba con Mongo 7 local. El índice parcial con `$in` requiere Mongo ≥ 6.
- **Render, GitHub Pages, GitHub Actions**: archivos escritos, nunca ejecutados. Docker en Render free no se verificó.
- **Imágenes Docker / `docker compose up`**: no se construyeron (sin demonio Docker); solo se validó la sintaxis.
- Pruebas visuales de la UI en móvil y accesibilidad con lector de pantalla: no realizadas.

## Pendiente / limitaciones declaradas
- **RUES y SIGEP**: deshabilitados. No se halló API ni dato abierto oficial verificado; no se hace scraping. Requiere decisión sobre un canal autorizado.
- **DUE / Buscando Colegio**: se usa el dataset de establecimientos educativos como aproximación; no confirmado como el mismo origen.
- Plantilla: solo 5 filas de educación superior y 2 de idiomas (se advierte; el excedente no se imprime).
- No hay recuperación de contraseña, verificación de correo, ni limitación de tasa global por IP.
- No se valida la autenticidad de certificados (fuera de alcance, declarado en la UI).
- La evidencia histórica corresponde a T-001. La revisión actual añade T-010 para el paso 1, sin aceptar tareas anteriores. El estado local previo del harness no estaba presente en esta copia; no se reconstruyen aceptaciones a partir de documentación histórica. La revisión final y aceptación siguen pendientes. No se ha publicado ni desplegado durante esta revisión.
