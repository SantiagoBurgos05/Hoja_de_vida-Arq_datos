from __future__ import annotations
from fastapi import APIRouter, Header, Request
from pydantic import BaseModel, EmailStr, field_validator
from ...core.deps import CurrentUser
from . import service

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Credentials(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def _len(cls, v: str) -> str:
        if len(v) < 10 or len(v) > 128:
            raise ValueError("La contraseña debe tener entre 10 y 128 caracteres")
        return v


@router.post("/register", status_code=201)
def register(c: Credentials):
    return service.register(c.email, c.password)


@router.post("/login")
def login(c: Credentials, request: Request):
    ip = request.client.host if request.client else "?"
    return service.login(c.email, c.password, ip)


@router.post("/logout", status_code=204)
def logout(authorization: str | None = Header(default=None), user=CurrentUser):
    service.logout(authorization[7:].strip())


@router.get("/me")
def me(user=CurrentUser):
    return {"id": str(user["_id"]), "email": user["email"]}
