# Despliegue (costo cero, dentro de planes gratuitos)

> Nada de esto fue ejecutado todavía (ver `estado.md`). Verifique límites vigentes en `limites-gratuitos.md`.

1. **GitHub**: suba el repositorio; Actions ejecuta `quality.yml` (pytest con Mongo de servicio + `harness validate` + build del frontend). `pages.yml` reutiliza `quality.yml` como primer job: si las pruebas o la compilación del mismo commit fallan, no se publica.
2. **MongoDB Atlas M0**: cree un cluster gratuito, un usuario de base de datos y permita la IP de Render. Copie la cadena `mongodb+srv://…` a `MONGO_URI`. La app crea colecciones, validadores e índices al arrancar (`init_db`). Compruebe en el arranque que `collMod` con `$jsonSchema` sea aceptado en M0; si no, la API sigue validando con Pydantic.
3. **Supabase**: cree un proyecto, un bucket **privado** `certificados` y copie `SUPABASE_URL` y la *service key* (solo al backend).
4. **Render**: Web Service desde `render.yaml` (Docker, plan free). Variables según `.env.example`. `CORS_ORIGINS` = URL de Pages. Se duerme a los 15 min; el frontend lo tolera con reintentos y aviso. `healthCheckPath` responde 503 si MongoDB no está disponible.
5. **GitHub Pages**: Settings → Pages → Source: *GitHub Actions*; defina la variable de repositorio `VITE_API_URL` con la URL de Render. `pages.yml` publica `frontend/dist`. Verifique si su plan permite Pages en repositorios privados.
6. **Mantenimiento (Gold, recuperación y retención)**: `render.yaml` genera `ADMIN_TOKEN` (`generateValue`); cópielo del panel de Render. En GitHub defina la variable de repositorio `API_URL` (URL de Render) y el secreto `ADMIN_TOKEN` (mismo valor). `.github/workflows/maintenance.yml` llama a diario a `POST /api/admin/maintenance` (también se puede lanzar a mano desde Actions). Sin esas dos variables el workflow termina con un aviso y no hace nada. Alternativa por consola: `cd backend && python -m app.maintenance`.
7. **Protección de recursos**: `TRUST_PROXY=true` en Render para que los límites por IP usen la IP real; `USER_STORAGE_QUOTA_MB` (25 MB por defecto) limita el espacio de soportes por usuario. Con 1 GB de Supabase, 25 MB por usuario cubre unas 40 personas al tope; ajuste según el uso real.
8. Antes de usar fuentes reales: confirme columnas de los datasets y ajuste `field_map` (`connectors/registry.py`).

## Local
`docker compose up --build` (web en :8080, API en :8000) o sin Docker: `MONGO_URI=… uvicorn app.main:app` y `npm run dev` en `frontend/`.

Para preparar las dependencias y repetir el recorrido de navegador y la prueba de permisos del volumen, siga [paso-01-local.md](paso-01-local.md). `python scripts/local_checks.py e2e` usa una fuente simulada y una base temporal; `python scripts/local_checks.py docker` comprueba imágenes y almacenamiento en un proyecto Compose de prueba independiente.
