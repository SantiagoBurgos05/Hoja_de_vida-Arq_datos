from __future__ import annotations
from fastapi import APIRouter
from ...core.deps import CurrentUser, oid
from . import service
from .models import ResumeIn, EducacionSuperiorIn, ExperienciaIn
from .timecalc import summarize

router = APIRouter(prefix="/api", tags=["resume"])
S = service.serialize


@router.get("/resume")
def get_resume(user=CurrentUser):
    return S(service.get_or_create_resume(user["_id"]))


@router.put("/resume")
def put_resume(body: ResumeIn, user=CurrentUser):
    return S(service.save_resume(user["_id"], body.model_dump()))


@router.get("/education")
def list_education(user=CurrentUser):
    return [S(r) for r in service.list_records(user["_id"], "education_higher")]


@router.post("/education", status_code=201)
def create_education(body: EducacionSuperiorIn, user=CurrentUser):
    return S(service.create_record(user["_id"], "education_higher", body.model_dump()))


@router.put("/education/{rid}")
def update_education(rid: str, body: EducacionSuperiorIn, user=CurrentUser):
    return S(service.update_record(user["_id"], "education_higher", oid(rid), body.model_dump()))


@router.delete("/education/{rid}", status_code=204)
def delete_education(rid: str, user=CurrentUser):
    service.delete_record(user["_id"], "education_higher", oid(rid))


@router.get("/work")
def list_work(user=CurrentUser):
    return [S(r) for r in service.list_records(user["_id"], "work")]


@router.post("/work", status_code=201)
def create_work(body: ExperienciaIn, user=CurrentUser):
    return S(service.create_record(user["_id"], "work", body.model_dump()))


@router.put("/work/{rid}")
def update_work(rid: str, body: ExperienciaIn, user=CurrentUser):
    return S(service.update_record(user["_id"], "work", oid(rid), body.model_dump()))


@router.delete("/work/{rid}", status_code=204)
def delete_work(rid: str, user=CurrentUser):
    service.delete_record(user["_id"], "work", oid(rid))


@router.get("/resume/experience-summary")
def experience_summary(user=CurrentUser):
    return summarize(service.list_records(user["_id"], "work"))
