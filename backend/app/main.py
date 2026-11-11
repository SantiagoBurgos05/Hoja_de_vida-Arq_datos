from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .core.config import get_settings
from .core.db import init_db, close_client, get_db
from .modules.identity.router import router as identity
from .modules.resume.router import router as resume
from .modules.organizations.router import router as organizations
from .modules.documents.router import router as documents
from .modules.lake.router import router as lake
from .modules.export.router import router as export


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    close_client()


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="Hoja de Vida Digital", version="0.1.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origins, allow_methods=["GET", "POST", "PUT", "DELETE"],
                       allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
                       expose_headers=["X-Export-Warnings", "Content-Disposition"])

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault("Cache-Control", "no-store")
        return resp

    @app.get("/api/health")
    def health():
        # MongoDB es una dependencia necesaria: si falla, 503 para que el alojamiento no considere sana la API.
        try:
            get_db().command("ping")
            return {"status": "ok", "db": "ok"}
        except Exception:
            return JSONResponse({"status": "degraded", "db": "error"}, status_code=503)

    for r in (identity, resume, organizations, documents, lake, export):
        app.include_router(r)
    return app


app = create_app()
