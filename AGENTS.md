# AGENTS.md — Reglas para agentes de IA y para la persona responsable

Proyecto: **Hoja de Vida Digital** (Formato Único de Hoja de Vida – Persona Natural, Colombia).
Modelo de desarrollo: *One-Person Company* con *harness engineering*.

## 1. Roles
| Rol | Quién | Puede | No puede |
|---|---|---|---|
| Dirección y aceptación | La persona responsable | Aprobar, rechazar, cambiar prioridades, ejecutar `harness.py close` | — |
| IA Análisis | Agente | Escribir/ajustar requisitos, criterios de aceptación en `docs/` y `harness/` | Tocar código en `backend/app` o `frontend/src` |
| IA Arquitectura | Agente | ADR, modelo de datos, esquemas, diagramas | Aceptar tareas |
| IA Desarrollo | Agente | Código y pruebas dentro de `allowed_paths` de la tarea | Modificar `harness/tasks.json` estados ni evidencias a mano |
| IA Revisión | Agente distinto al de desarrollo | Revisar diff, ejecutar checks, emitir veredicto | Escribir código de producción |

Una tarea solo la acepta la persona. La IA nunca marca `accepted`.

## 2. Flujo obligatorio (máquina de estados)
`pending → ready → running → checking → review → accepted`; `blocked` tras 3 fallos de checks.
Un **commit nuevo invalida** checks y revisión de la tarea (hay que repetir `check` y `review`).
Comandos: `python scripts/harness.py validate | start T-xxx | check T-xxx | review T-xxx --verdict ok|changes --notes "..." | close T-xxx | status`.

## 3. Reglas del repositorio
1. Cada cambio de comportamiento exige prueba automatizada y evidencia en `harness/evidence/` vinculada al hash de commit.
2. Código y documentación se mantienen sincronizados: si cambia un endpoint, estado o colección, se actualiza `docs/` en el mismo cambio (`harness.py validate` comprueba que cada endpoint documentado exista y viceversa).
3. **Nunca** presentar como hecho algo pendiente. `docs/estado.md` es la fuente de verdad: separa *Probado*, *Implementado sin probar en vivo* y *Pendiente*.
4. Solo datos **sintéticos** en pruebas y ejemplos. Prohibido subir documentos de identidad reales al repositorio.
5. Secretos solo por variables de entorno; `.env` está en `.gitignore`.
6. El navegador **nunca** habla con MongoDB ni con el almacenamiento: todo pasa por la API.
7. Verificación de entidades: se verifica por **identificador oficial** en el backend; la similitud de nombre no concede verificación. Ante error, restricción o ambigüedad se conserva el borrador **sin** conceder verificación.
8. Los espacios de **firma** y **Observaciones del Jefe de Recursos Humanos** no se completan automáticamente (ni en datos ni en el PDF).
9. Conectores a fuentes externas: solo hosts de la lista blanca (`ALLOWED_CONNECTOR_HOSTS`), solo APIs/datos abiertos oficiales; scraping prohibido salvo permiso expreso documentado en `docs/fuentes.md`.

## 4. Mapa del código
- `backend/app/core` config, seguridad, base de datos, esquemas Mongo, errores.
- `backend/app/modules/<modulo>` identity, resume, organizations, documents, lake, export (monolito modular; los módulos solo se hablan por sus `service.py`).
- `frontend/src` React + Vite.
- `harness/` catálogo (`features.json`), tareas (`tasks.json`), evidencias.
- `docs/` documentación versionada.

## 5. Definición de «hecho»
Una tarea está hecha cuando: criterios de aceptación cumplidos, checks verdes, evidencia vinculada al commit, revisión `ok` por un rol distinto al que desarrolló, aceptación humana.
