from __future__ import annotations
from typing import Literal
from fastapi import APIRouter, Response
from ...core.deps import AdminOnly
from . import service

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[AdminOnly])


@router.post("/maintenance")
def maintenance(response: Response, trigger: Literal["manual", "schedule"] = "manual"):
    """Ejecuta el mantenimiento completo. 200 si todos los pasos terminaron bien; 500 si alguno falló (detalle en el cuerpo)."""
    r = service.run_maintenance(trigger)
    if not r["ok"]:
        response.status_code = 500
    return r


@router.get("/maintenance")
def maintenance_runs():
    """Últimas ejecuciones del mantenimiento."""
    return service.last_runs()
