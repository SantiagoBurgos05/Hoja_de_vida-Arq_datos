# ADR 01 — Monolito modular

**Estado:** aceptada

## Contexto
Una persona desarrolla y opera; costo cero; pocos usuarios.

## Decisión
Un solo servicio FastAPI con módulos (identity, resume, organizations, documents, lake, export) que se comunican por servicios.

## Consecuencias
Despliegue simple en Render free; fronteras claras para extraer servicios después. Sin tolerancia a fallos independiente por módulo.
