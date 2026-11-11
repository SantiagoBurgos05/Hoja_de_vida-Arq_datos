from __future__ import annotations
from typing import Literal, Optional
from fastapi import APIRouter, File, Form, Header, Response, UploadFile
from ...core.config import get_settings
from ...core.deps import CurrentUser, oid
from ...core.ratelimit import enforce
from ...core.errors import bad
from . import service

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("", status_code=201)
def upload(response: Response, record_type: Literal["education_basic", "education_higher", "work"] = Form(...),
           record_id: str = Form(...), file: UploadFile = File(...),
           idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"), user=CurrentUser):
    enforce("upload", str(user["_id"]), get_settings().rate_upload)
    max_b = get_settings().max_upload_bytes
    data = file.file.read(max_b + 1)           # nunca se lee más de 5 MB + 1 byte
    if idempotency_key is not None and not (8 <= len(idempotency_key) <= 80):
        raise bad("idempotency_key_invalida", "Idempotency-Key debe tener entre 8 y 80 caracteres.")
    doc, result = service.upload(user["_id"], record_type, oid(record_id), file.filename, file.content_type, data, idempotency_key)
    if result != "created":
        response.status_code = 200
    return {**service.public(doc), "result": result}


@router.get("")
def list_documents(record_type: Optional[Literal["education_basic", "education_higher", "work"]] = None,
                   record_id: Optional[str] = None, user=CurrentUser):
    return [service.public(d) for d in service.list_docs(user["_id"], record_type, oid(record_id) if record_id else None)]


@router.get("/usage")
def usage(user=CurrentUser):
    """Espacio usado por los soportes del usuario frente a su cuota."""
    return service.usage(user["_id"])


@router.get("/{doc_id}/download")
def download(doc_id: str, user=CurrentUser):
    d, data = service.read_bytes(user["_id"], oid(doc_id))
    return Response(content=data, media_type=d["content_type"], headers={
        "Content-Disposition": f'attachment; filename="{d["filename"]}"',
        "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})


@router.delete("/{doc_id}", status_code=204)
def delete(doc_id: str, user=CurrentUser):
    service.delete(user["_id"], oid(doc_id))
