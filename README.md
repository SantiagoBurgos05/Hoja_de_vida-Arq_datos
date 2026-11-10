# Hoja de Vida Digital

Aplicación web para diligenciar el **Formato Único de Hoja de Vida – Persona Natural** (Colombia): registro/sesión, datos persistentes, verificación de entidades en fuentes oficiales, soportes recuperables, exportación a PDF sobre el formato oficial.

Stack: React + Vite · FastAPI (monolito modular) · MongoDB · Supabase Storage privado · Docker. Desarrollo con *harness engineering* (ver `AGENTS.md`).

## Inicio rápido (local)
```bash
# Backend (requiere un MongoDB)
cd backend && pip install -r requirements-dev.txt
MONGO_URI=mongodb://127.0.0.1:27017 uvicorn app.main:app --reload
# Pruebas (MongoDB real)
TEST_MONGO_URI=mongodb://127.0.0.1:27017 python -m pytest
# Frontend
cd frontend && npm install && npm run dev && npm test
# Harness
python scripts/harness.py validate && python scripts/harness.py status
# E2E (con backend, frontend preview y fuente simulada levantados; ver tests_e2e/)
python tests_e2e/e2e.py
```
Documentación: `docs/` (estado real en `docs/estado.md`). **Lea `estado.md` antes de afirmar que algo funciona en producción.**
