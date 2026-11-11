# Estado real del proyecto (2026-11-11)

Fuente de verdad: lo que NO está en «Probado» no debe presentarse como hecho.

## Revisión actual: RUES y SIGEP habilitados (2026-11-11)

- **RUES** con el dataset oficial de Confecámaras `c82u-588k` (sincronizado con el RUES) y **SIGEP** con el «Universo de entidades» de Función Pública `h7zv-k39x`. Consultados **en vivo**: Bancolombia por NIT y nombre, MinEducación por código SIGEP `0011`, NIT compartido del Distrito. Se excluyen personas naturales y datos de representantes; NIT de relleno no se consulta; varias matrículas activas = ambiguo.
- Backend **142 pruebas aprobadas** (incluye 9 nuevas de RUES/SIGEP); frontend 13 y compilación; E2E 15, ahora con **empresa verificada por NIT y certificado laboral adjunto** (fuente simulada). `check_sources.py` en vivo: las 5 fuentes correctas.
- **Desplegado** (`93b5e30` en Render y Pages; `check_deploy.py` correcto) y **probado en la URL pública por la persona responsable**: Fiduciaria Bogotá S.A. (NIT 800142383, matrícula CANCELADA según la fuente) buscada por NIT con dígito de verificación y **verificada**, con carga de certificado laboral habilitada (2026-11-11).
- La persona responsable informó que el recorrido completo de la app funciona en la URL pública (registro, datos, verificación, soportes, exportación). Sin revisión ni aceptación formal en el harness (T-010 a T-014).

## Revisión anterior: paso 5 — infraestructura (2026-11-11)

- **Atlas M0 probado en vivo** con `scripts/check_atlas.py` desde el PC local (MongoDB 8.0.37, host `hv-cluster.zkltgmq.mongodb.net`): conexión, `init_db` (colecciones con `$jsonSchema` e índices), `init_db` repetido (`collMod`, permiso `dbAdmin`), validador que rechaza un documento inválido, índices único/parcial/TTL, y escritura y borrado de un evento sintético: **todo correcto**.
- Acceso de red limitado por ahora a la IP del PC; falta habilitar el acceso de Render.
- **Supabase Storage probado en vivo** con `scripts/check_supabase.py` (bucket `certificados` privado, clave secreta de servicio): carga, tamaño, descarga idéntica, acceso sin credenciales denegado y borrado: **correctos**. Hallazgos: (1) una `SUPABASE_URL` copiada de la Data API (`…/rest/v1/`) rompía todas las rutas: el adaptador ahora usa solo esquema y host; (2) el bucket restringido a PDF/JPG/PNG **rechaza la evidencia JSON** de las verificaciones de entidades, lo que hacía fallar la verificación con HTTP 500: ahora responde `organization_status = error` sin conceder verificación, y el script lo comprueba. Se desactivó la restricción de tipos del bucket y el script pasó completo, incluida la evidencia JSON. **Recorrido por la API** (Mongo local temporal, SNIES real, Supabase real, usuario y certificado sintéticos): verificación de UNIMINUTO (2829) → carga `ready` en Supabase → descarga idéntica → borrado coordinado (objeto ausente): **correcto**. Los objetos de prueba se eliminaron del bucket.
- **Render desplegado** (`https://hoja-de-vida-api-eeal.onrender.com`, Docker, plan free) y comprobado con `scripts/check_deploy.py` el 2026-11-11: `/api/health` 200 con Atlas conectado, cabeceras de seguridad, 401 sin sesión y 403 sin token de administración: **correctos**. **CORS falló**: `CORS_ORIGINS` se configuró con mayúsculas y los navegadores envían el origen en minúsculas, así que la página de Pages quedaría bloqueada. Se corrigió la variable a minúsculas y la API ahora normaliza los orígenes (cambio de código pendiente de desplegar). **Segunda ejecución: todo correcto** — CORS permite `https://santiagoburgos05.github.io` y rechaza un origen ajeno; `POST /api/admin/maintenance` en Render completó todos sus pasos (Atlas, Supabase y Gold).
- **GitHub Actions** sobre `dec5687`: `quality` (backend con Mongo de servicio + frontend) **aprobado** en GitHub. `deploy-pages` falló primero porque la rama por defecto era `paso-02-consistencia` y el entorno `github-pages` solo permitía esa rama; se cambió la rama por defecto a `main`, se permitió `main` en el entorno y el workflow quedó **aprobado**.
- **GitHub Pages publicado**: `https://santiagoburgos05.github.io/Hoja_de_vida-Arq_datos/` responde 200, el JavaScript publicado apunta a `https://hoja-de-vida-api-eeal.onrender.com` (no a `localhost`) y la pantalla de acceso carga sin errores de consola (2026-11-11).
- **Pendiente (paso 6)**: recorrido completo por una persona en la URL pública (registro, datos, nueva sesión, verificación SNIES, certificado, descarga en otro navegador, exportación). Workflow `maintenance` en GitHub: sin confirmar. Las correcciones posteriores a `dec5687` no están desplegadas.
- Además: el check del harness ya no registra un intento cuando MongoDB no responde, y sus propios archivos no cuentan como cambios sin commit. `check T-010` pasó completo (incluido `docker:smoke`) sobre `dec5687` con cambios sin commit.

## Revisión anterior: paso 4 (2026-11-10, Windows)

- Mantenimiento operativo: `POST /api/admin/maintenance` (y `python -m app.maintenance`) expira cargas interrumpidas, completa borrados pendientes, aplica la retención, concilia Silver y reconstruye Gold; registra cada ejecución. Workflow diario `maintenance.yml` escrito, **no ejecutado en GitHub**.
- Cuota de soportes por usuario (25 MB, 413) con `GET /api/documents/usage` visible en la interfaz; límites de uso en registro, consultas a fuentes y cargas (429).
- Backend: **125 pruebas aprobadas**; frontend 13 y compilación; E2E 15. Sin revisión ni aceptación humana (T-013). Detalle: [paso-04-operacion.md](paso-04-operacion.md).

## Revisión anterior: paso 3 (2026-11-10, Windows)

- Fuentes educativas **consultadas en vivo** en datos.gov.co: SNIES (`n5yy-8nav`), SIET (`gpje-sixt`) y establecimientos (`cfw5-qzt5`). Las columnas supuestas de SNIES y establecimientos eran incorrectas y se corrigieron; establecimientos repite cada colegio por año y ahora se usa el año más reciente.
- `scripts/check_sources.py` en vivo: búsqueda, verificación por identificador e identificador inexistente correctos en las tres fuentes. Recorrido por la API con SNIES real: verificación de la entidad y carga de un certificado sintético correctas.
- Backend: **114 pruebas aprobadas**; frontend 13 y compilación; E2E 15 (fuente simulada con columnas reales).
- Límites: SNIES con actualización 2022-07-08 y SIET con corte 11/2020; RUES/SIGEP seguían deshabilitados en ese momento (habilitados después, ver revisión actual). Sin revisión ni aceptación humana (T-012). Detalle: [paso-03-fuentes.md](paso-03-fuentes.md).

## Revisión anterior: paso 2 (2026-11-10, Windows, rama `paso-02-consistencia`)

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
- ~~Consultas a fuentes oficiales~~: resuelto en el paso 3 (consultadas en vivo, columnas confirmadas). La suite automatizada sigue usando respuestas simuladas; la consulta en vivo es `scripts/check_sources.py`.
- **Supabase Storage**: probado en vivo desde el PC el 2026-11-11 (ver revisión actual); **no** probado todavía desde Render.
- **MongoDB Atlas**: probado desde el PC local el 2026-11-11 (M0, MongoDB 8.0.37): `$jsonSchema`, `collMod` e índices funcionan. **No** probado todavía desde Render ni con carga real.
- **Render, GitHub Pages, GitHub Actions**: archivos escritos, nunca ejecutados. Docker en Render free no se verificó.
- **Imágenes Docker / `docker compose up`**: no se construyeron (sin demonio Docker); solo se validó la sintaxis.
- Pruebas visuales de la UI en móvil y accesibilidad con lector de pantalla: no realizadas.

## Fuera de alcance (decisión de la dirección, 2026-11-11)
Proyecto con fines **educativos**: probar y demostrar las tecnologías implementadas, no operar un servicio abierto al público. Por decisión de la persona responsable **no se implementan**:
- Recuperación de contraseña y verificación de correo (requerirían un servicio de correo). Usar solo cuentas y datos sintéticos.
- Impresión del excedente de la plantilla (más de 5 estudios superiores o 2 idiomas): se mantiene la advertencia en la exportación.

## Pendiente / limitaciones declaradas
- **RUES y SIGEP**: habilitados con datos abiertos oficiales (Confecámaras y Función Pública). No cubren personas naturales comerciantes, matrículas antiguas sin NIT ni entidades públicas liquidadas (ver `docs/fuentes.md`).
- **DUE / Buscando Colegio**: se usa el dataset de establecimientos educativos como aproximación; no confirmado como el mismo origen.
- Plantilla: solo 5 filas de educación superior y 2 de idiomas (se advierte; el excedente no se imprime).
- No hay recuperación de contraseña ni verificación de correo. Hay límites de uso en registro, consultas a fuentes y cargas (paso 4), no un límite global para todas las rutas.
- No se valida la autenticidad de certificados (fuera de alcance, declarado en la UI).
- La evidencia histórica corresponde a T-001. La revisión actual añade T-010 para el paso 1, sin aceptar tareas anteriores. El estado local previo del harness no estaba presente en esta copia; no se reconstruyen aceptaciones a partir de documentación histórica. La revisión final y aceptación siguen pendientes. No se ha publicado ni desplegado durante esta revisión.
