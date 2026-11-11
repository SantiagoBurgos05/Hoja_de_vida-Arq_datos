# Paso 1: recorrido local reproducible

Fecha: 2026-11-10 (America/Bogota). Tarea: T-010. Estado: comprobaciones locales aprobadas; cierre pendiente de Docker y aceptación humana.

## Alcance y documentación revisada

Se revisó íntegramente `Documentacion/Hoja_de_Vida_Digital_Arquitectura.pdf` (16 páginas, versión 2.0), junto con requisitos, arquitectura, estado, despliegue y reglas del repositorio.

El núcleo esperado es: registro y acceso; borradores persistentes; verificación de entidades por identificador oficial; soportes privados recuperables en otra sesión; exportación sobre la plantilla; catálogo y linaje Bronze/Silver/Gold; comprobaciones y revisión antes de la aceptación humana. Verificar una entidad no acredita la trayectoria ni la autenticidad del certificado.

El PDF y el catálogo implementado usan numeraciones RF/ADR diferentes. Por ejemplo, el PDF dedica RF02 a recuperación y RF08 a estados/procedencia; el catálogo actual dedica RF02 a datos personales y RF08 al Data Lake. T-006 aparece como caso de certificados en el PDF y como Data Lake en `harness/tasks.json`. Se registra esta diferencia sin renumerar silenciosamente tareas, pruebas o evidencia histórica.

T-010 es una validación nueva del código existente, autorizada por el paso 1 del plan adjunto. No declara aceptadas T-001 a T-009 ni altera sus dependencias. Los pasos 2 a 6 requieren el aval posterior del responsable.

## Cambios del paso 1

- `backend/requirements-dev.txt`: declara `pdfplumber`, cuya ausencia impedía recopilar las pruebas de exportación, y Playwright para el E2E.
- `backend/Dockerfile`: crea `/data/storage` y asigna su propiedad al usuario de la API antes de `USER app`. La comprobación con un volumen Docker nuevo está preparada, pero pendiente de ejecutar.
- `frontend/.dockerignore`: excluye dependencias de Windows, compilaciones y archivos de entorno del contexto de construcción Linux.
- `scripts/harness.py`: resuelve el ejecutable `npm.cmd` en Windows y registra los checks cerrados `local:e2e` y `docker:smoke`. Dos pruebas adicionales cubren resolución del comando y herramienta ausente.
- `scripts/local_checks.py`: automatiza los servicios del E2E y la comprobación de Docker. El E2E usa puertos libres, base de datos aleatoria y almacenamiento temporal; detiene sus procesos y elimina su base al terminar. La compilación del E2E no modifica `frontend/dist`.
- `.gitignore`: excluye entorno virtual, caché de pytest y salidas locales de comprobación.

## Resultados reproducidos en esta revisión

Entorno: Windows, Python 3.14.5, Node 24.18.0, MongoDB 8.2.6 instalado en el PC. MongoDB se inició en `127.0.0.1:27028` con un directorio de datos separado; no se usaron bases de datos habituales del usuario.

| Comprobación | Resultado |
|---|---|
| Backend completo contra MongoDB real | 89 pruebas aprobadas (87 existentes + 2 del harness) |
| Frontend | 8 pruebas aprobadas |
| Compilación del frontend | Aprobada |
| E2E Chromium: registro, edición, autoguardado, recarga, nueva sesión, verificación simulada, carga/descarga idéntica de soporte, experiencia, PDF, aislamiento y consola | 14 comprobaciones aprobadas |
| Coherencia de endpoints y documentación | `harness.py validate`: aprobada |
| Sintaxis de Compose | `docker compose config --quiet`: aprobada |
| Construcción y ejecución de contenedores; permisos y persistencia del volumen | Pendiente: acceso denegado al canal local `dockerDesktopLinuxEngine` desde la sesión aislada |

El E2E espera a que termine el autoguardado. No demuestra que se conserve un cambio al navegar antes de 1,2 segundos: esa corrección corresponde al paso 2. La fuente educativa del E2E es un servidor local simulado, no SNIES en vivo. Los resultados nativos de Windows no sustituyen la validación de las imágenes Linux ni la de Atlas, Supabase o el despliegue público.

No se generó cobertura nueva: el archivo `backend/.coverage` ya figuraba eliminado antes de estos cambios. También era preexistente la carpeta no versionada `docs/Documentacion/`; se conserva intacta.

## Repetir las comprobaciones en Windows

Desde la raíz del repositorio, con MongoDB disponible y Docker Desktop iniciado:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m playwright install chromium
npm --prefix frontend ci
$env:PYTHONUTF8 = '1'
$env:TEST_MONGO_URI = 'mongodb://127.0.0.1:27017'
Push-Location backend
..\.venv\Scripts\python.exe -m pytest
Pop-Location
npm --prefix frontend test
npm --prefix frontend run build
.\.venv\Scripts\python.exe scripts/harness.py validate
.\.venv\Scripts\python.exe scripts/local_checks.py e2e
.\.venv\Scripts\python.exe scripts/local_checks.py docker
```

Use en `TEST_MONGO_URI` el puerto de su instancia local. Las pruebas crean bases con nombres aleatorios. El check Docker construye las imágenes API/web, levanta MongoDB y ejecuta dos contenedores de API: uno escribe un archivo sintético sin root y otro verifica su persistencia y lo borra. Al terminar elimina únicamente los recursos de su proyecto Compose aleatorio `hvcheck-*`. No inicia ni borra los volúmenes del proyecto Compose habitual. Un volumen antiguo con permisos incorrectos debe diagnosticarse aparte, preservando sus datos.

El script E2E guarda capturas, PDF sintético y logs en `.local-checks/e2e/`, o en `E2E_OUT` si está definido. Las fuentes siguen siendo simuladas.

## Evidencias y cierre

`python scripts/harness.py check T-010` ejecuta los checks registrados y genera evidencia automáticamente en `harness/evidence/`. Un fallo de Docker mantiene la tarea sin aprobar; no se omite ni se transforma en éxito. No repetir el check completo para el mismo bloqueo sin resolverlo: el harness bloquea tras tres fallos.

El `HEAD` base de esta revisión es `03c5ff536c5c2ab09f4d31142d52c72f034f9366`. Los cambios están sin commit y el harness registra `dirty: true`. No es todavía una entrega aceptada ligada a un commit definitivo. La mejora de vigencia por huella del contenido queda para el trabajo posterior del harness.

Una revisión independiente del código del paso 1 no encontró hallazgos accionables; comprobó también la ejecución de `npm.CMD` desde Python en Windows. Esta revisión no acredita la construcción ni los permisos del volumen Docker. No se ha registrado un veredicto final en el harness porque falta ese check obligatorio.

Para cerrar el paso: resolver el acceso a Docker o ejecutar `scripts/local_checks.py docker` desde una consola externa; conservar el resultado; repetir los checks del harness sobre el cambio definitivo; obtener revisión favorable y aceptación humana. No ejecutar `close` ni avanzar al paso 2 sin el aval del responsable.
