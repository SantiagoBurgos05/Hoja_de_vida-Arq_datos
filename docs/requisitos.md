# Requisitos

Base: Formato Único de Hoja de Vida – Persona Natural (Leyes 190/1995, 489 y 443/1998), 3 páginas, 6 secciones.

## Requisitos funcionales
| ID | Requisito | Sección FUHV |
|---|---|---|
| RF01 | Registro e inicio/cierre de sesión | — |
| RF02 | Datos personales editables y persistentes | 1 |
| RF03 | Formación académica: básica/media (último grado), superior (modalidad TC/TL/TE/UN/ES/MG/DOC, semestres, graduado, fecha, tarjeta profesional) e idiomas (habla/lee/escribe R/B/MB) | 2 |
| RF04 | Experiencia laboral (actual + anteriores), con cálculo del tiempo total | 3 y 4 |
| RF05 | Búsqueda y verificación de entidades por identificador oficial (SNIES, SIET, DUE/Buscando Colegio, RUES, SIGEP) | 2 y 3 |
| RF06 | Soportes PDF/JPG/PNG ≤ 5 MB, habilitados solo tras verificar la entidad; recuperables en sesiones futuras | 2 y 3 |
| RF07 | Exportación a PDF sobre la plantilla oficial; firma y Observaciones RR.HH. en blanco | 5 y 6 |
| RF08 | Data lake Bronze/Silver/Gold con catálogo, linaje y control de duplicados | — |
| RF09 | Guardado concurrente seguro (`revision`, 409) y borrado coordinado de soportes | — |

## Distinciones obligatorias (no se pueden mezclar)
1. **Entidad verificada**: la organización existe en una fuente oficial (`organization_status = verified`).
2. **Antecedente declarado**: lo que el usuario afirma (estudió/trabajó allí). `record_status = declared`.
3. **Soporte adjunto**: archivo cargado (`record_status = supported`, `document_status = ready`). La autenticidad queda `not_validated`.

Verificar una organización **no** acredita que el usuario estudió o trabajó allí **ni** autentica el certificado.

## Requisitos no funcionales
- Seguridad: Argon2id, sesiones opacas con hash en BD, límite de intentos, CORS restringido, autorización por propietario (404 si el recurso es ajeno), descargas con `nosniff`.
- Usabilidad: autoguardado, estados visibles (guardado/sin conectar/conflicto), borradores siempre conservados, lenguaje claro en español.
- Costo cero: Render free, Atlas M0, Supabase free, GitHub Pages (ver `limites-gratuitos.md`).
- Privacidad: Gold sin datos personales (supresión si la celda la aportan menos de k = 5 personas distintas).

## Fuera de alcance (declarado)
- Autenticación de certificados ante la entidad emisora.
- Firma electrónica; la firma es manuscrita en el PDF impreso.
- Integración RUES/SIGEP en vivo (sin API oficial verificada): conectores deshabilitados por defecto.
