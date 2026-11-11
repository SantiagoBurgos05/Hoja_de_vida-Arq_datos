import httpx
import pytest
from app.core.db import get_db
from .helpers import SNIES_ROWS, edu_payload, mock_source, reset_connectors, work_payload


@pytest.fixture(autouse=True)
def _clean():
    reset_connectors()
    yield
    reset_connectors()


def verify(client, u, source, oid, rt=None, rid=None):
    body = {"source": source, "official_id": oid}
    if rt:
        body.update(record_type=rt, record_id=rid)
    return client.post("/api/organizations/verify", json=body, headers=u["headers"])


def test_busqueda_lista_coincidencias_sin_conceder_verificacion(client, alice):
    mock_source("snies", SNIES_ROWS)
    before = get_db().organizations.count_documents({})
    r = client.post("/api/organizations/search", json={"source": "snies", "query": "universidad sintetica", "municipio": "bogota"}, headers=alice["headers"]).json()
    assert len(r["candidates"]) == 3 and r["organization_status"] == "pending"
    assert get_db().organizations.count_documents({}) == before           # buscar no verifica ni guarda


def test_verificar_por_identificador_oficial_guarda_evidencia(client, alice):
    mock_source("snies", SNIES_ROWS)
    e = client.post("/api/education", json=edu_payload(), headers=alice["headers"]).json()
    r = verify(client, alice, "snies", "1101", "education_higher", e["id"]).json()
    assert r["organization_status"] == "verified"
    o = r["organization"]
    assert o["official_id"] == "1101" and o["source"] == "snies" and o["estado_registral"] == "Activa en la Fecha de Actualizacion (2022-07-08)" and o["verified_at"] and o["evidence_id"]
    assert "NO acredita" in r["message"]
    rec = client.get("/api/education", headers=alice["headers"]).json()[0]
    assert rec["organization_status"] == "verified" and rec["organization_id"] == o["id"]
    # la evidencia existe en Bronze con su huella
    from bson import ObjectId
    ev = get_db().lake_objects.find_one({"_id": ObjectId(o["evidence_id"])})
    assert ev["kind"] == "org_evidence" and ev["layer"] == "bronze" and ev["sha256"] == o["evidence_sha256"]
    uid = get_db().users.find_one({"email": alice["email"]})["_id"]
    v = list(get_db().org_verifications.find({"user_id": uid}))
    assert len(v) == 1 and v[0]["organization_status"] == "verified" and v[0]["official_id"] == "1101" and v[0]["queried_at"]


def test_similitud_de_nombre_no_basta_identificador_exacto(client, alice):
    """Hay 3 entidades con nombre casi igual; '110' (prefijo) no es un identificador oficial existente."""
    mock_source("snies", SNIES_ROWS)
    e = client.post("/api/education", json=edu_payload(), headers=alice["headers"]).json()
    r = verify(client, alice, "snies", "110", "education_higher", e["id"]).json()
    assert r["organization_status"] == "not_found" and r["organization"] is None
    assert client.get("/api/education", headers=alice["headers"]).json()[0]["organization_status"] == "not_found"
    # y '1101' coincide exacto aunque exista '11010'
    assert verify(client, alice, "snies", "1101", "education_higher", e["id"]).json()["organization"]["name"] == "UNIVERSIDAD SINTETICA DEL NORTE"


def test_fuente_caida_conserva_borrador_sin_verificar(client, alice):
    mock_source("snies", boom=httpx.ConnectTimeout("lento"))
    before = get_db().organizations.count_documents({})
    e = client.post("/api/education", json=edu_payload(), headers=alice["headers"]).json()
    r = verify(client, alice, "snies", "1101", "education_higher", e["id"])
    assert r.status_code == 200 and r.json()["organization_status"] == "error" and "borrador se conserva" in r.json()["message"]
    rec = client.get("/api/education", headers=alice["headers"]).json()[0]
    assert rec["organization_status"] == "error" and rec["organization_id"] is None and rec["nombre_estudios"] == "Ingeniería de Sistemas"
    assert get_db().organizations.count_documents({}) == before


@pytest.mark.parametrize("status,body", [(500, "[]"), (200, "no es json"), (200, '{"a":1}'), (403, "[]")])
def test_respuestas_anomalas_no_verifican(client, alice, status, body):
    mock_source("snies", status=status, body=body)
    e = client.post("/api/education", json=edu_payload(), headers=alice["headers"]).json()
    assert verify(client, alice, "snies", "1101", "education_higher", e["id"]).json()["organization_status"] == "error"


def test_ambiguo_no_concede(client, alice):
    dup = [SNIES_ROWS[0], dict(SNIES_ROWS[0], nombre_instituci_n="OTRA CON EL MISMO ID")]
    mock_source("snies", dup)
    e = client.post("/api/education", json=edu_payload(), headers=alice["headers"]).json()
    r = verify(client, alice, "snies", "1101", "education_higher", e["id"]).json()
    assert r["organization_status"] == "pending" and "ambiguo" in r["message"]


def test_fallo_transitorio_no_revoca_verificacion_previa(client, alice):
    mock_source("snies", SNIES_ROWS)
    e = client.post("/api/education", json=edu_payload(), headers=alice["headers"]).json()
    assert verify(client, alice, "snies", "1101", "education_higher", e["id"]).json()["organization_status"] == "verified"
    mock_source("snies", status=503, body="[]")
    assert verify(client, alice, "snies", "1101", "education_higher", e["id"]).json()["organization_status"] == "error"
    assert client.get("/api/education", headers=alice["headers"]).json()[0]["organization_status"] == "verified"


def test_fuente_deshabilitable_por_configuracion(client, alice):
    """DISABLED_SOURCES apaga una fuente sin cambiar código: no consulta, no verifica, conserva el borrador."""
    from app.core.config import get_settings
    s = get_settings()
    old = s.disabled_sources
    s.disabled_sources = ["rues", "sigep"]
    try:
        _run_fuente_deshabilitada(client, alice)
    finally:
        s.disabled_sources = old


def _run_fuente_deshabilitada(client, alice):
    w = client.post("/api/work", json=work_payload(), headers=alice["headers"]).json()
    r = verify(client, alice, "rues", "900000000", "work", w["id"]).json()
    assert r["organization_status"] == "pending" and "RUES" in r["message"]
    s = client.post("/api/organizations/search", json={"source": "sigep", "query": "ministerio"}, headers=alice["headers"]).json()
    assert s["candidates"] == [] and s["organization_status"] == "pending"
    assert client.get("/api/work", headers=alice["headers"]).json()[0]["organization_status"] == "pending"


def test_fuente_debe_corresponder_al_tipo_de_registro_y_de_entidad(client, alice):
    mock_source("siet", SNIES_ROWS)
    e = client.post("/api/education", json=edu_payload(), headers=alice["headers"]).json()
    assert verify(client, alice, "due", "1101", "education_higher", e["id"]).status_code == 422
    w = client.post("/api/work", json=work_payload(tipo_entidad="publica"), headers=alice["headers"]).json()
    assert verify(client, alice, "rues", "1", "work", w["id"]).status_code == 422      # pública => SIGEP
    w2 = client.post("/api/work", json=work_payload(tipo_entidad=None), headers=alice["headers"]).json()
    assert verify(client, alice, "rues", "1", "work", w2["id"]).status_code == 422     # sin tipo de entidad


def test_no_se_puede_vincular_registro_ajeno(client, alice, bob):
    mock_source("snies", SNIES_ROWS)
    e = client.post("/api/education", json=edu_payload(), headers=alice["headers"]).json()
    assert verify(client, bob, "snies", "1101", "education_higher", e["id"]).status_code == 404
    assert client.get("/api/education", headers=alice["headers"]).json()[0]["organization_status"] == "pending"


def test_host_no_permitido_se_bloquea(client, alice):
    from app.core import config
    s = config.get_settings()
    old = s.allowed_connector_hosts
    s.allowed_connector_hosts = ["otro.example.com"]
    try:
        calls = []
        mock_source("snies", SNIES_ROWS, calls=calls)
        e = client.post("/api/education", json=edu_payload(), headers=alice["headers"]).json()
        assert verify(client, alice, "snies", "1101", "education_higher", e["id"]).json()["organization_status"] == "error"
        assert calls == []        # ni siquiera se hizo la petición
    finally:
        s.allowed_connector_hosts = old


def test_consulta_soql_escapa_comillas(client, alice):
    calls = []
    mock_source("snies", [], calls=calls)
    client.post("/api/organizations/search", json={"source": "snies", "query": "x' OR '1'='1"}, headers=alice["headers"])
    assert "X''" in calls[0].replace("%27", "'")                 # la comilla del usuario queda escapada


def test_busqueda_exige_criterio(client, alice):
    assert client.post("/api/organizations/search", json={"source": "snies"}, headers=alice["headers"]).status_code == 422
    assert client.post("/api/organizations/search", json={"source": "snies", "query": "x"}).status_code == 401


def test_organizacion_unica_por_fuente_e_id(client, alice, bob):
    mock_source("snies", SNIES_ROWS)
    for u in (alice, bob):
        e = client.post("/api/education", json=edu_payload(), headers=u["headers"]).json()
        verify(client, u, "snies", "1101", "education_higher", e["id"])
    assert get_db().organizations.count_documents({"source": "snies", "official_id": "1101"}) == 1
    assert get_db().org_verifications.count_documents({}) >= 2
