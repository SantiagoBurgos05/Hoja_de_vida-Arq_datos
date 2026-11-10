# ADR 04 — Control optimista por revisión

**Estado:** aceptada

## Contexto
Varias pestañas o dispositivos pueden editar la misma hoja de vida.

## Decisión
Campo `revision`; `PUT` con revisión distinta ⇒ 409 con la versión del servidor; UI ofrece resolver.

## Consecuencias
Sin bloqueos largos; el usuario decide en conflicto.
