# ADR 05 — Data lake lógico Bronze/Silver/Gold sobre Mongo + Storage

**Estado:** aceptada

## Contexto
Se requiere trazabilidad y métricas sin información personal con presupuesto cero.

## Decisión
Bronze = originales en Storage con catálogo; Silver = estandarizado sin identificadores directos; Gold = agregados con umbral de privacidad k≥5 contado sobre **personas distintas** (no registros); linaje por `derived_from`.

Actualización (paso 2, T-011): Silver se sincroniza con cada cambio del registro operacional (creación, modificación, verificación, soportes y eliminación). Al eliminar un registro se borra su fila Silver y su objeto de catálogo queda `deleted: true`, de modo que Gold no cuenta registros eliminados. Gold sigue siendo una reconstrucción controlada con `ADMIN_TOKEN`.

Actualización (paso 4, T-013): la reconstrucción de Gold y la conciliación de Silver forman parte del mantenimiento diario (`POST /api/admin/maintenance`, programado por `.github/workflows/maintenance.yml`), junto con la recuperación de cargas interrumpidas y borrados pendientes. Cada ejecución queda registrada en `maintenance_runs`.

## Consecuencias
Escala limitada al plan gratuito (0,5 GB Atlas, 1 GB Storage). Gold se calcula bajo demanda con token de administración.
