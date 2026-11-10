from __future__ import annotations
import httpx
from app.modules.organizations.connectors import registry
from app.modules.organizations.connectors.socrata import SocrataConnector

SNIES_ROWS = [
    {"codigo_institucion": "1101", "nombre_institucion": "UNIVERSIDAD SINTETICA DEL NORTE", "municipio_domicilio": "BOGOTA", "departamento_domicilio": "BOGOTA D.C.", "estado_institucion": "Activa"},
    {"codigo_institucion": "11010", "nombre_institucion": "UNIVERSIDAD SINTETICA DEL NORTE SEDE 2", "municipio_domicilio": "BOGOTA", "departamento_domicilio": "BOGOTA D.C.", "estado_institucion": "Activa"},
    {"codigo_institucion": "2202", "nombre_institucion": "UNIVERSIDAD SINTETICA DEL NORTE", "municipio_domicilio": "MEDELLIN", "departamento_domicilio": "ANTIOQUIA", "estado_institucion": "Activa"},
]


def mock_source(source: str, rows=None, status=200, boom: Exception | None = None, body: str | None = None, calls: list | None = None):
    kind, ds, fm = registry._DEFS[source]

    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(str(request.url))
        if boom:
            raise boom
        if body is not None:
            return httpx.Response(status, text=body)
        return httpx.Response(status, json=rows if rows is not None else [])
    registry.set_connector(source, SocrataConnector(source, kind, ds, fm, transport=httpx.MockTransport(handler)))


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
