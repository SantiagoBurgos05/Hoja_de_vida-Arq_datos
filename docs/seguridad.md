# Seguridad

| Control | Implementación | Prueba |
|---|---|---|
| Contraseñas | Argon2id; mínimo 10 caracteres | test_identity |
| Sesión | Token opaco aleatorio; en BD solo SHA-256; TTL 7 días; logout lo elimina | test_identity |
| Fuerza bruta | 5 fallos/15 min por correo+IP ⇒ 429 | test_identity |
| Enumeración | Registro duplicado con mensaje genérico | test_identity |
| Autorización | Filtro por `user_id`; ajeno ⇒ 404 | test_resume, test_documents, test_lake |
| Campos del servidor | Modelos `extra=forbid`: el cliente no puede declararse `verified`/`supported` | test_resume |
| Archivos | Tamaño ≤ 5 MB (lectura acotada), firma real (PDF/JPEG/PNG), tipo declarado coherente, nombre saneado, clave sin nombre del usuario, descarga como adjunto con `nosniff`, huella verificada al descargar | test_documents |
| Conectores | Solo lista blanca de hosts, sin redirecciones, timeout 8 s, ≤ 1 MB, consulta escapada | test_organizations |
| CORS / cabeceras | Orígenes explícitos; `nosniff`, `no-referrer`, `no-store` | test_export (cabeceras) |
| Admin | `build-gold` exige `ADMIN_TOKEN`; vacío ⇒ deshabilitado | test_lake |
| Datos reales | Prohibidos en repo y pruebas; solo sintéticos | AGENTS.md |

**Compromiso conocido:** el token vive en `sessionStorage` (sin cookies ⇒ sin CSRF) pero un XSS podría leerlo; por eso no se usa `dangerouslySetInnerHTML`. HTTPS lo aportan Render/GitHub Pages (no probado aquí). No hay limitación de tasa global por IP más allá del login (pendiente).
