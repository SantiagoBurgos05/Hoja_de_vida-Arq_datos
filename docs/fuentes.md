# Fuentes oficiales de verificación

Estado a 2026-11-11. Las cinco fuentes se **consultaron en vivo** en datos.gov.co (API SODA/Socrata) y sus columnas se confirmaron contra los metadatos de cada dataset (`/api/views/<id>.json`). La comprobación se repite con `python scripts/check_sources.py` (requiere internet; deja evidencia en `.local-checks/sources/`, no versionada).

| Tipo | Fuente | Dataset (publicador) | Identificador oficial | Columnas usadas | Estado registral que se guarda | Estado |
|---|---|---|---|---|---|---|
| Educación superior | SNIES | `n5yy-8nav` «MEN_INSTITUCIONES EDUCACIÓN SUPERIOR» (MinEducación). 361 filas, código único por institución principal o seccional | `c_digo_instituci_n` (número) | `nombre_instituci_n`, `municipio_domicilio`, `departamento_domicilio`, `n_mero_identificaci_n` (NIT), `estado`, `fecha_actualizacion` | `estado (fecha_actualizacion)`, p. ej. «Activa en la Fecha de Actualizacion (2022-07-08)» | **Probado en vivo** |
| Educación para el trabajo | SIET | `gpje-sixt` «MEN_INSTITUCIONES EDUCACIÓN PARA EL TRABAJO Y EL DESARROLLO HUMANO» (MinEducación). 3 976 filas, código único | `codigo_institucion` (número) | `nombre_institucion`, `municipio`, `departamento`, `nit`, `licencia`, `mes_corte`, `a_o_corte` | Sin columna de estado: «Licencia de funcionamiento N; corte MM/AAAA» | **Probado en vivo**. Último corte publicado: **11/2020** |
| Colegios | DUE / Buscando Colegio (aproximación) | `cfw5-qzt5` «MEN_ESTABLECIMIENTOS_EDUCATIVOS_PREESCOLAR_BÁSICA_Y_MEDIA» (MinEducación). Un registro por establecimiento **y año** (2015–2025) | `codigo_dane` (número, 12 dígitos) | `nombre_establecimiento`, `municipio`, `departamento`, `a_o` | «Reportado en el directorio del MEN, año AAAA» (año más reciente del código) | **Probado en vivo**. No se confirmó que sea el mismo origen que Buscando Colegio |
| Empresas privadas | RUES | `c82u-588k` «Personas Naturales, Personas Jurídicas y Entidades Sin Ánimo de Lucro» (**Confecámaras**, operador del RUES; datos sincronizados con el RUES; licencia CC BY-SA 4.0). 9,4 M de filas, actualizado 2026-11-06 | `nit` sin dígito de verificación (8–10 dígitos) | `razon_social`, `camara_comercio` (no hay columna de municipio), `estado_matricula`, `matricula`, `ultimo_ano_renovado` y otras de la entidad | `estado_matricula; matrícula N (cámara); último año renovado AAAA` | **Probado en vivo** |
| Entidades públicas | SIGEP | `h7zv-k39x` «Universo de entidades» (**Función Pública**, que administra el SIGEP; CC BY-SA 4.0). 6 404 entidades activas | `dm_institucion_cod_institucion` = código SIGEP (coincide con el directorio de MinTIC `kqut-4h4r`; único) | `nombre`, `ccb_nit_inst` (NIT), `municipio`, `departamento`, `orden`, `estado_ins` | `ACTIVA en el Universo de entidades (Función Pública); orden …` | **Probado en vivo** |

## Comportamiento del conector (`connectors/socrata.py`, `registry.py`)

- **Búsqueda por nombre**: `upper(columna) like '%P_L_T_CN_C_%'`. SoQL no tiene `unaccent`; cada vocal se convierte en el comodín de un carácter, así «politecnico» encuentra «POLITÉCNICO». Los `%`/`_` del usuario se neutralizan y las comillas se escapan. Ampliar la búsqueda no afecta la verificación, que es por identificador exacto.
- **Búsqueda por NIT** (SNIES, SIET): si el identificador tiene 9 o más dígitos se busca por la columna NIT. La fuente usa formatos variables («892.300.285-6», «830103627 - 1»): se filtra en la consulta por los 9 dígitos base y se compara exactamente en el backend. El NIT se muestra junto a cada candidato. **Una institución con seccionales comparte NIT**: se verifica el código de la sede elegida.
- **Verificación**: siempre por la columna del identificador oficial con igualdad exacta. Un identificador con formato no numérico no se consulta y responde `not_found`.
- **Datasets por periodo (DUE)**: se ordena por `a_o DESC` y se toma solo el año más reciente en que aparece el código. Varios años del mismo código **no** son ambigüedad; el mismo código repetido en el mismo año **sí** lo es (existe al menos un caso real en 2025) y no se concede verificación.
- La evidencia en Bronze guarda la respuesta cruda y el dataset consultado.
- **RUES**:
  - **Privacidad**: toda consulta excluye `PERSONA NATURAL` (7 M de filas con nombres y documentos de personas) y pide solo columnas de la entidad (`$select`): nunca nombres ni documentos de representantes legales. Así tampoco quedan en la evidencia guardada.
  - **Identificador**: NIT de 8 a 10 dígitos. Los NIT de relleno («1», etc.) no se consultan. La búsqueda acepta el NIT con dígito de verificación (`890903938-8`).
  - **Varias matrículas con el mismo NIT** (p. ej. canceladas por traslado de domicilio y una activa): si exactamente una está `ACTIVA` se usa esa; si hay varias activas (NIT de relleno `999999999`) es **ambiguo** y no se verifica.
  - **Empresa cancelada**: se verifica (existió en el registro) y el estado registral lo dice; no se presenta como vigente.
  - Matrículas antiguas sin NIT en la fuente no se pueden verificar.
  - Consulta por nombre sobre 9,4 M de filas: 1–4 s; tiempo máximo propio de 20 s.
- **SIGEP**: se verifica por código SIGEP. El NIT se repite entre dependencias (p. ej. `899999061`, Distrito de Bogotá): la búsqueda por NIT lista las dependencias y la persona elige. Las columnas de correo, dirección y representante no se piden. Solo contiene entidades activas: una entidad liquidada no aparece.
- **Interruptor operativo**: `DISABLED_SOURCES=rues,sigep` (variable de entorno) apaga fuentes sin cambiar código; la consulta responde `pending` y se conserva el borrador.

## Reglas
- Solo APIs/datos abiertos oficiales. Scraping **no** se implementa.
- Hosts permitidos: `ALLOWED_CONNECTOR_HOSTS` (por defecto `www.datos.gov.co`).
- Timeout 8 s, sin redirecciones a otros hosts, respuesta limitada a 1 MB.
- Error, timeout, restricción o ambigüedad ⇒ `organization_status = error|pending`; el borrador se conserva y **no** se concede verificación.
- Se guarda: entidad, fuente, identificador, fecha de consulta, estado registral reportado y evidencia (respuesta cruda + hash).

## Límites conocidos
1. **Antigüedad**: SNIES informa `fecha_actualizacion` 2022-07-08 en todas sus filas; SIET tiene corte 11/2020. Una institución creada después no aparecerá. Se informa el corte en el estado registral para no presentarlo como estado actual.
2. **Instituciones cerradas**: SNIES y SIET solo listan instituciones vigentes en su corte. DUE conserva años anteriores (desde 2015), por lo que un colegio cerrado después de 2015 sí se encuentra.
3. DUE/Buscando Colegio: origen no confirmado como idéntico.
4. RUES y SIGEP usan **datos abiertos** oficiales, no las consultas en línea de rues.org.co ni de SIGEP (no hay API pública y el scraping está prohibido). Su actualización depende de la publicación en datos.gov.co (RUES: semanal en la práctica; Universo de entidades: periódica).
5. Personas naturales comerciantes (trabajo para una persona natural con matrícula mercantil): no se verifican, por privacidad; el registro queda declarado sin verificación.
