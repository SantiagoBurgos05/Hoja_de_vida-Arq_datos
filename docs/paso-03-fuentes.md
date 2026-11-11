# Paso 3: verificación educativa con fuentes reales

Fecha: 2026-11-10 (America/Bogota). Tarea: T-012 (depende de T-011). Rama: `paso-02-consistencia`. Estado: implementado y probado en vivo localmente; **sin revisión registrada ni aceptación humana**.

## Qué se encontró al consultar datos.gov.co

- **SNIES** (`n5yy-8nav`): las columnas supuestas eran incorrectas (`codigo_institucion` → `c_digo_instituci_n`, `nombre_institucion` → `nombre_instituci_n`, `estado_institucion` → `estado`). Con el código anterior **ninguna** verificación real habría funcionado.
- **SIET** (`gpje-sixt`): `codigo_institucion`, `nombre_institucion`, `municipio` y `departamento` eran correctas; **no existe columna de estado**. Último corte: 11/2020.
- **Establecimientos** (`cfw5-qzt5`): la columna de municipio es `municipio` (no `nombre_municipio`), no hay columna de estado y **cada colegio se repite por año** (2015–2025). Con el código anterior toda verificación de colegio habría resultado «ambigua».
- Las columnas de identificador son numéricas; la comparación con literal de texto funciona en la API.

## Cambios

- `registry.py`: columnas confirmadas, plantilla de estado registral por fuente, identificador numérico y columna de corte (`a_o`) para DUE. Nueva función `make()`.
- `socrata.py`: búsqueda tolerante a tildes, búsqueda por NIT con comparación exacta de dígitos, deduplicación por corte, validación del formato del identificador y validación de que cada fila sea un objeto.
- Interfaz: el NIT se muestra junto a cada candidato.
- `scripts/check_sources.py`: comprobación en vivo (búsqueda, verificación de la primera coincidencia e identificador inexistente). Registrado en el harness como check `live:sources`.
- Pruebas: filas sintéticas con la estructura real de cada dataset (no se versionan filas reales). `fake_socrata.py` del E2E usa las columnas reales e interpreta el `LIKE` de SoQL.

## Resultados

| Comprobación | Resultado |
|---|---|
| Backend (`pytest`, MongoDB 8.2.6 local) | **114 aprobadas** (104 + 10 de `test_fuentes.py`) |
| Frontend: pruebas y compilación | 13 aprobadas; compilación correcta |
| E2E Chromium (fuente simulada con columnas reales) | 15 comprobaciones aprobadas |
| `scripts/check_sources.py` **en vivo** | SNIES: «minuto de dios» + Bogotá → 2 coincidencias; verificado 2829. SIET: verificado 1112 (licencia y corte). DUE: «san bartolome» + Bogotá → 4 coincidencias; verificado con año 2025. Identificadores inexistentes: sin coincidencias |
| Recorrido por la API con SNIES real (usuario y certificado sintéticos, base temporal) | Búsqueda → verificación de 2829 → carga de certificado `ready`; identificador inexistente → `not_found` |
| Búsquedas en vivo adicionales | NIT `800116217-2` → 2829 (Bogotá) y 2841 (Bello); «politecnico» → instituciones con «POLITÉCNICO/POLITECNICO» |

## Pendiente

- **RUES/SIGEP**: requiere decisión de la dirección (canal oficial autorizado o revisión administrativa trazable). Sin ello la experiencia laboral no admite certificados.
- La consulta en vivo depende de internet y de datos.gov.co; la suite automatizada no la ejecuta (usa respuestas simuladas).
- Confirmar si DUE/Buscando Colegio tiene un origen distinto a `cfw5-qzt5`.
