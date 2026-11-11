from __future__ import annotations
import httpx
from app.modules.organizations.connectors import registry

# Filas SINTÉTICAS con las columnas reales del dataset SNIES n5yy-8nav (confirmadas 2026-11-10, docs/fuentes.md).
def snies_row(code, name, municipio, departamento, nit="900.000.000-1"):
    return {"c_digo_instituci_n": code, "nombre_instituci_n": name, "n_mero_identificaci_n": nit, "principal_seccional": "Principal",
            "departamento_domicilio": departamento, "municipio_domicilio": municipio,
            "estado": "Activa en la Fecha de Actualizacion", "fecha_actualizacion": "2022-07-08"}


SNIES_ROWS = [
    snies_row("1101", "UNIVERSIDAD SINTETICA DEL NORTE", "BOGOTA", "BOGOTA D.C."),
    snies_row("11010", "UNIVERSIDAD SINTETICA DEL NORTE SEDE 2", "BOGOTA", "BOGOTA D.C."),
    snies_row("2202", "UNIVERSIDAD SINTETICA DEL NORTE", "MEDELLIN", "ANTIOQUIA"),
]


def mock_source(source: str, rows=None, status=200, boom: Exception | None = None, body: str | None = None, calls: list | None = None):

    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(str(request.url))
        if boom:
            raise boom
        if body is not None:
            return httpx.Response(status, text=body)
        return httpx.Response(status, json=rows if rows is not None else [])
    registry.set_connector(source, registry.make(source, transport=httpx.MockTransport(handler)))


def reset_connectors():
    for s in ("snies", "siet", "due", "rues", "sigep"):
        registry.set_connector(s, None)


def edu_payload(**kw):
    base = {"modalidad": "UN", "semestres_aprobados": 10, "graduado": True, "nombre_estudios": "Ingeniería de Sistemas",
            "terminacion": {"mes": 12, "anio": 2024}, "tarjeta_profesional": "TP-123", "institucion_declarada": "Universidad Sintetica del Norte"}
    base.update(kw)
    return base


def work_payload(**kw):
    base = {"es_actual": False, "empresa_declarada": "Empresa Sintetica SAS", "tipo_entidad": "privada",
            "categoria_tiempo": "empleado_privado", "pais": "Colombia", "departamento": "Cundinamarca", "municipio": "Bogotá",
            "fecha_ingreso": "2020-01-01", "fecha_retiro": "2021-12-31", "cargo": "Analista", "dependencia": "TI",
            "direccion": "Calle 1 # 2-3", "telefonos": "3000000000", "correo_entidad": "rrhh@empresa.example.com"}
    base.update(kw)
    return base


def verified_education(client, user, official_id="1101"):
    """Crea un registro de educación superior y lo verifica con el conector simulado."""
    mock_source("snies", SNIES_ROWS)
    e = client.post("/api/education", json=edu_payload(), headers=user["headers"]).json()
    r = client.post("/api/organizations/verify", json={"source": "snies", "official_id": official_id, "record_type": "education_higher", "record_id": e["id"]}, headers=user["headers"])
    assert r.status_code == 200 and r.json()["organization_status"] == "verified", r.text
    return e["id"]
