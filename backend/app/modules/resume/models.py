"""Modelos de entrada (validación). Los campos gestionados por el servidor
(organization_id, organization_status, record_status, user_id) NO están aquí:
el cliente no puede declararse «verificado»."""
from __future__ import annotations
from datetime import date
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, EmailStr

Nivel = Literal["R", "B", "MB"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LibretaMilitar(Strict):
    clase: Optional[Literal["primera", "segunda"]] = None
    numero: Optional[str] = Field(None, max_length=30)
    dm: Optional[str] = Field(None, max_length=10)


class Direccion(Strict):
    pais: Optional[str] = Field(None, max_length=60)
    departamento: Optional[str] = Field(None, max_length=60)
    municipio: Optional[str] = Field(None, max_length=60)
    direccion: Optional[str] = Field(None, max_length=160)
    telefono: Optional[str] = Field(None, max_length=30)
    email: Optional[EmailStr] = None


class LugarNacimiento(Strict):
    fecha: Optional[date] = None
    pais: Optional[str] = Field(None, max_length=60)
    departamento: Optional[str] = Field(None, max_length=60)
    municipio: Optional[str] = Field(None, max_length=60)


class Personal(Strict):
    primer_apellido: str = Field("", max_length=60)
    segundo_apellido: str = Field("", max_length=60)
    nombres: str = Field("", max_length=80)
    tipo_documento: Optional[Literal["CC", "CE", "PAS"]] = None
    numero_documento: str = Field("", max_length=30)
    sexo: Optional[Literal["F", "M"]] = None
    nacionalidad: Optional[Literal["COL", "EXTRANJERO"]] = None
    pais_nacionalidad: str = Field("", max_length=60)
    libreta_militar: LibretaMilitar = LibretaMilitar()
    nacimiento: LugarNacimiento = LugarNacimiento()
    correspondencia: Direccion = Direccion()


class FechaMesAnio(Strict):
    mes: Optional[int] = Field(None, ge=1, le=12)
    anio: Optional[int] = Field(None, ge=1900, le=2100)


class EducacionBasica(Strict):
    ultimo_grado: Optional[int] = Field(None, ge=1, le=11)
    titulo_obtenido: str = Field("", max_length=120)
    fecha_grado: FechaMesAnio = FechaMesAnio()
    institucion_declarada: str = Field("", max_length=160)


class Idioma(Strict):
    idioma: str = Field(..., min_length=1, max_length=40)
    habla: Nivel
    lee: Nivel
    escribe: Nivel


class ResumeIn(Strict):
    revision: int = Field(..., ge=0)
    personal: Personal
    education_basic: EducacionBasica
    languages: list[Idioma] = Field(default_factory=list, max_length=10)


class EducacionSuperiorIn(Strict):
    revision: Optional[int] = Field(None, ge=0)
    modalidad: Literal["TC", "TL", "TE", "UN", "ES", "MG", "DOC"]
    semestres_aprobados: Optional[int] = Field(None, ge=0, le=20)
    graduado: Optional[bool] = None
    nombre_estudios: str = Field("", max_length=160)
    terminacion: FechaMesAnio = FechaMesAnio()
    tarjeta_profesional: str = Field("", max_length=40)
    institucion_declarada: str = Field("", max_length=160)


class ExperienciaIn(Strict):
    revision: Optional[int] = Field(None, ge=0)
    es_actual: bool = False
    empresa_declarada: str = Field("", max_length=160)
    tipo_entidad: Optional[Literal["publica", "privada"]] = None
    categoria_tiempo: Literal["servidor_publico", "empleado_privado", "independiente"]
    pais: str = Field("", max_length=60)
    departamento: str = Field("", max_length=60)
    municipio: str = Field("", max_length=60)
    correo_entidad: Optional[EmailStr] = None
    telefonos: str = Field("", max_length=40)
    fecha_ingreso: Optional[date] = None
    fecha_retiro: Optional[date] = None
    cargo: str = Field("", max_length=120)
    dependencia: str = Field("", max_length=120)
    direccion: str = Field("", max_length=160)
