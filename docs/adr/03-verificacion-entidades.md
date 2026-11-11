# ADR 03 — Verificación por identificador oficial y estados separados

**Estado:** aceptada

## Contexto
Parecerse al nombre de una entidad no prueba que exista ni que el usuario estuvo allí.

## Decisión
Verificar en backend con consulta exacta por identificador; separar entidad verificada / antecedente declarado / soporte adjunto; ante error o ambigüedad no se concede.

## Consecuencias
Más pasos para el usuario; resultados honestos. RUES y SIGEP deshabilitados hasta tener canal oficial autorizado (no se hace scraping).

Actualización 2026-11-11 (T-014): se habilitan con datos abiertos oficiales publicados en datos.gov.co por los operadores (Confecámaras para el RUES, Función Pública para el SIGEP). Siguen sin scraping. Las consultas excluyen personas naturales y datos de representantes; cualquier fuente puede apagarse con `DISABLED_SOURCES`.
