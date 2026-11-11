"""Paso 2: persistencia y consistencia (Silver sincronizado, umbral Gold por personas,
invalidación de verificaciones, idempotencia por operación completa, health)."""
import httpx
import pytest
from bson import ObjectId
from app.core.db import get_db
from app.modules.organizations.connectors import registry
from app.modules.organizations.connectors.socrata import SocrataConnector
from .conftest import PDF
from .helpers import SNIES_ROWS, edu_payload, mock_source, reset_connectors, verified_education, work_payload
from .test_documents import up

RUES_ROWS = [{"codigo_institucion": "900000001", "nombre_institucion": "EMPRESA SINTETICA SAS", "municipio_domicilio": "BOGOTA",
              "departamento_domicilio": "BOGOTA D.C.", "estado_institucion": "ACTIVA"}]


@pytest.fixture(autouse=True)
def _clean():
    reset_connectors()
    yield
    reset_connectors()


def _uid(u):
    return get_db().users.find_one({"email": u["email"]})["_id"]


def _mock_rues():
    """RUES está deshabilitado en producción; en pruebas se inyecta un conector simulado para ejercer el flujo."""
    _, ds, fm = registry._DEFS["snies"]
    tr = httpx.MockTransport(lambda req: httpx.Response(200, json=RUES_ROWS))
    registry.set_connector("rues", SocrataConnector("rues", "company", ds, fm, transport=tr))


def _verified_work(client, u):
    _mock_rues()
    w = client.post("/api/work", json=work_payload(tipo_entidad="privada"), headers=u["headers"]).json()
    r = client.post("/api/organizations/verify", json={"source": "rues", "official_id": "900000001", "record_type": "work",
                                                       "record_id": w["id"]}, headers=u["headers"])
    assert r.json()["organization_status"] == "verified", r.text
    return client.get("/api/work", headers=u["headers"]).json()[0]


# ------------------------------------------------------------------ Silver
def test_silver_se_crea_y_actualiza_con_el_registro(client, alice):
    e = client.post("/api/education", json=edu_payload(nombre_estudios="Física"), headers=alice["headers"]).json()
    s = get_db().silver_records.find_one({"owner_id": _uid(alice), "source_id": e["id"]})
    assert s and s["data"]["nombre_estudios"] == "FISICA"
    client.put(f"/api/education/{e['id']}", json=edu_payload(nombre_estudios="Química", revision=e["revision"]), headers=alice["headers"])
    s = get_db().silver_records.find_one({"owner_id": _uid(alice), "source_id": e["id"]})
    assert s["data"]["nombre_estudios"] == "QUIMICA"


def test_eliminar_registro_retira_su_copia_silver(client, alice):
    e = client.post("/api/education", json=edu_payload(), headers=alice["headers"]).json()
    w = client.post("/api/work", json=work_payload(), headers=alice["headers"]).json()
    db, uid = get_db(), _uid(alice)
    assert db.silver_records.count_documents({"owner_id": uid}) == 2
    lo = db.silver_records.find_one({"owner_id": uid, "source_id": e["id"]})["lake_object_id"]
    assert client.delete(f"/api/education/{e['id']}", headers=alice["headers"]).status_code == 204
    assert client.delete(f"/api/work/{w['id']}", headers=alice["headers"]).status_code == 204
    assert db.silver_records.count_documents({"owner_id": uid}) == 0
    assert db.lake_objects.find_one({"_id": lo})["deleted"] is True          # el catálogo conserva el hecho


def test_refresh_silver_retira_copias_huerfanas(client, alice):
    e = client.post("/api/education", json=edu_payload(), headers=alice["headers"]).json()
    db, uid = get_db(), _uid(alice)
    db.education_records.delete_one({"_id": ObjectId(e["id"])})               # borrado fuera del servicio (p. ej. versión anterior)
    r = client.post("/api/lake/refresh-silver", headers=alice["headers"]).json()
    assert r["removed"] == 1 and db.silver_records.count_documents({"owner_id": uid}) == 0


def test_gold_no_cuenta_registros_eliminados(client, make_user):
    db = get_db()
    db.silver_records.delete_many({}); db.gold_metrics.delete_many({})
    users = [make_user() for _ in range(5)]
    ids = [client.post("/api/education", json=edu_payload(modalidad="MG"), headers=u["headers"]).json()["id"] for u in users]
    client.delete(f"/api/education/{ids[0]}", headers=users[0]["headers"])    # quedan 4 personas => se suprime
    client.post("/api/lake/build-gold", headers={"X-Admin-Token": "test-admin"})
    dims = {(g["metric"], g["dimension"]) for g in client.get("/api/lake/gold", headers=users[1]["headers"]).json()}
    assert ("educacion_por_modalidad", "MG") not in dims


def test_gold_umbral_por_personas_distintas_no_por_registros(client, make_user):
    db = get_db()
    db.silver_records.delete_many({}); db.gold_metrics.delete_many({})
    one = make_user()
    for _ in range(6):                                                        # una persona, seis registros
        client.post("/api/education", json=edu_payload(modalidad="TE"), headers=one["headers"])
    client.post("/api/lake/build-gold", headers={"X-Admin-Token": "test-admin"})
    assert get_db().gold_metrics.count_documents({"dimension": "TE"}) == 0
    others = [make_user() for _ in range(4)]
    for u in others:
        client.post("/api/education", json=edu_payload(modalidad="TE"), headers=u["headers"])
    client.post("/api/lake/build-gold", headers={"X-Admin-Token": "test-admin"})
    g = get_db().gold_metrics.find_one({"metric": "educacion_por_modalidad", "dimension": "TE"})
    assert g["personas"] == 5 and g["value"] == 10


# ------------------------------------------------- verificación e invalidación
def test_silver_refleja_verificacion_y_soporte(client, alice):
    rid = verified_education(client, alice)
    s = get_db().silver_records.find_one({"owner_id": _uid(alice), "source_id": rid})
    assert s["data"]["organization_status"] == "verified" and s["data"]["fuente_entidad"] == "snies"
    up(client, alice, rid)
    s = get_db().silver_records.find_one({"owner_id": _uid(alice), "source_id": rid})
    assert s["data"]["record_status"] == "supported"
    lo = get_db().lake_objects.find_one({"_id": s["lake_object_id"]})
    assert len(lo["derived_from"]) == 1


def test_cambiar_tipo_entidad_invalida_la_verificacion(client, alice):
    w = _verified_work(client, alice)
    assert w["organization_status"] == "verified" and w["organization_id"]
    r = client.put(f"/api/work/{w['id']}", json=work_payload(tipo_entidad="publica", categoria_tiempo="servidor_publico", revision=w["revision"]),
                   headers=alice["headers"])
    assert r.status_code == 200, r.text
    assert r.json()["organization_status"] == "pending" and r.json()["organization_id"] is None
    s = get_db().silver_records.find_one({"owner_id": _uid(alice), "source_id": w["id"]})
    assert s["data"]["organization_status"] == "pending" and s["data"]["tipo_entidad"] == "publica"


def test_otros_cambios_conservan_la_verificacion(client, alice):
    w = _verified_work(client, alice)
    r = client.put(f"/api/work/{w['id']}", json=work_payload(tipo_entidad="privada", cargo="Coordinador", revision=w["revision"]),
                   headers=alice["headers"]).json()
    assert r["organization_status"] == "verified" and r["organization_id"] == w["organization_id"]


def test_no_cambia_tipo_entidad_con_soportes_cargados(client, alice):
    w = _verified_work(client, alice)
    assert up(client, alice, w["id"], rt="work").status_code == 201
    w = client.get("/api/work", headers=alice["headers"]).json()[0]
    r = client.put(f"/api/work/{w['id']}", json=work_payload(tipo_entidad="publica", revision=w["revision"]), headers=alice["headers"])
    assert r.status_code == 409 and r.json()["detail"]["code"] == "soportes_existentes"
    w2 = client.get("/api/work", headers=alice["headers"]).json()[0]
    assert w2["tipo_entidad"] == "privada" and w2["organization_status"] == "verified" and w2["revision"] == w["revision"]


# ------------------------------------------------------------- idempotencia
def test_idempotencia_misma_clave_otro_registro_es_conflicto(client, alice):
    r1 = verified_education(client, alice)
    r2 = verified_education(client, alice)
    a = up(client, alice, r1, PDF, key="clave-otro-reg-01")
    assert a.status_code == 201
    b = up(client, alice, r2, PDF, key="clave-otro-reg-01")
    assert b.status_code == 409 and b.json()["detail"]["code"] == "idempotency_key_reutilizada"
    assert client.get(f"/api/documents?record_id={r2}", headers=alice["headers"]).json() == []


def test_fallo_de_almacenamiento_libera_la_clave_para_reintentar(client, alice):
    from app.core import storage as st
    rid = verified_education(client, alice)
    real = st.get_storage()

    class Falla:
        def put(self, *a, **k):
            raise st.StorageError("caido")

        def delete(self, *a, **k):
            pass
    st.set_storage(Falla())
    try:
        assert up(client, alice, rid, PDF, key="clave-reintento-01").status_code == 502
    finally:
        st.set_storage(real)
    r = up(client, alice, rid, PDF, key="clave-reintento-01")
    assert r.status_code == 201 and r.json()["document_status"] == "ready"


# --------------------------------------------------------------------- health
def test_health_devuelve_503_si_mongo_falla(client, monkeypatch):
    assert client.get("/api/health").status_code == 200
    import app.main as main

    class Caida:
        def command(self, *a):
            raise RuntimeError("sin conexión")
    monkeypatch.setattr(main, "get_db", lambda: Caida())
    r = client.get("/api/health")
    assert r.status_code == 503 and r.json()["db"] == "error"
