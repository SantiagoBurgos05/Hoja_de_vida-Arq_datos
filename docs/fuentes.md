# Fuentes oficiales de verificación

Estado a 2026-11-10. **Ninguna fuente fue consultada en vivo** desde el entorno de desarrollo (sin acceso a los sitios oficiales); los conectores se probaron con respuestas simuladas.

| Tipo | Fuente | Vía | Identificador oficial | Estado |
|---|---|---|---|---|
| Educación superior | SNIES (MEN) | Datos abiertos Socrata, `datos.gov.co` dataset `n5yy-8nav` | código de institución | Conector escrito; nombres de campo **por confirmar** contra el dataset real |
| Educación para el trabajo | SIET | Socrata `gpje-sixt` | código de institución SIET | Igual |
| Colegios | DUE / Buscando Colegio | Socrata `cfw5-qzt5` (establecimientos educativos) usado como aproximación; no se confirmó que sea el mismo origen que Buscando Colegio | código DANE | Igual; **supuesto declarado** |
| Empresas privadas | RUES | Sin API ni dataset abierto oficial verificado; términos no legibles | NIT | **Deshabilitado por defecto**. Requiere canal autorizado |
| Entidades públicas | SIGEP | Sin API verificada. Candidato: dataset «Directorio Georreferenciado de Entidades Públicas» (`kqut-4h4r`, identificado solo por título) | código/NIT | **Deshabilitado por defecto** |

## Reglas
- Solo APIs/datos abiertos oficiales. Scraping **no** se implementa.
- Hosts permitidos: `ALLOWED_CONNECTOR_HOSTS` (por defecto `www.datos.gov.co`).
- Timeout 8 s, sin redirecciones a otros hosts, respuesta limitada a 1 MB.
- Error, timeout, restricción o ambigüedad ⇒ `organization_status = error|pending`; el borrador se conserva y **no** se concede verificación.
- Se guarda: entidad, fuente, identificador, fecha de consulta, estado registral reportado y evidencia (respuesta mínima + hash).

## Pendiente de confirmar antes de producción
1. Nombres reales de columnas de cada dataset (ajustar `field_map` en `connectors/socrata.py`).
2. Si Buscando Colegio/DUE tiene un origen distinto a `cfw5-qzt5`.
3. Canal autorizado para RUES y SIGEP.
