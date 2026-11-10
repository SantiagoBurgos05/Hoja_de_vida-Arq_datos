from __future__ import annotations
from fastapi import APIRouter, Response
from ...core.deps import CurrentUser, audit
from . import service

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/preview")
def preview(user=CurrentUser):
    """Advertencias de exportación (límites físicos de la plantilla) sin generar el PDF."""
    return {"warnings": service.warnings_for(service.collect(user["_id"]))}


@router.get("/pdf")
def pdf(user=CurrentUser):
    data, warnings = service.build_pdf(user["_id"])
    audit(user["_id"], "export_pdf", warnings=len(warnings))
    return Response(content=data, media_type="application/pdf", headers={
        "Content-Disposition": 'attachment; filename="hoja_de_vida.pdf"',
        "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store",
        "X-Export-Warnings": str(len(warnings))})
