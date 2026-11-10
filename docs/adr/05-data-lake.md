# ADR 05 — Data lake lógico Bronze/Silver/Gold sobre Mongo + Storage

**Estado:** aceptada

## Contexto
Se requiere trazabilidad y métricas sin información personal con presupuesto cero.

## Decisión
Bronze = originales en Storage con catálogo; Silver = estandarizado sin identificadores directos; Gold = agregados con k-anonimato (k≥5); linaje por `derived_from`.

## Consecuencias
Escala limitada al plan gratuito (0,5 GB Atlas, 1 GB Storage). Gold se calcula bajo demanda con token de administración.
