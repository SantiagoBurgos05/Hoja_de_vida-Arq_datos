# Estado real del proyecto (2026-11-10)

Fuente de verdad: lo que NO está en «Probado» no debe presentarse como hecho.

## Probado (ejecutado en este entorno; pruebas en el repositorio)
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
- Solo la tarea T-001 se recorrió por el harness (start/check, evidencia en `harness/evidence/` ligada al commit local); revisión y aceptación (`review`/`close`) y el resto de tareas las debe ejecutar la persona responsable. El repositorio git es local; no se publicó en GitHub.
