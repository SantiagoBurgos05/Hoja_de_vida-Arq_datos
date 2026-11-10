# ADR 02 — El navegador nunca toca Mongo ni Storage

**Estado:** aceptada

## Contexto
Las credenciales de bases y de almacenamiento no pueden vivir en el cliente.

## Decisión
Todo acceso pasa por la API; Storage con bucket privado y clave de servicio solo en el backend.

## Consecuencias
Descargas pasan por el backend (consumen egress de Render/Supabase); control de autorización centralizado.
