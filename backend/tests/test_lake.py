import pytest
from bson import ObjectId
from app.core.db import get_db
from .conftest import PDF
from .helpers import edu_payload, reset_connectors, verified_education, work_payload
from .test_documents import up


@pytest.fixture(autouse=True)
def _clean():
    reset_connectors()
    yield
    reset_connectors()


def test_catalogo_bronze_y_linaje_silver(client, alice):
    rid = verified_education(client, alice)
    d = up(client, alice, rid).json()
    r = client.post("/api/lake/refresh-silver", headers=alice["headers"]).json()
    assert r["silver_records"] >= 1
    cat = client.get("/api/lake/catalog", headers=alice["headers"]).json()
    layers = {c["layer"] for c in cat}
    assert {"bronze", "silver"} <= layers
    cert = [c for c in cat if c["kind"] == "certificate"][0]
    assert cert["sha256"] == d["sha256"]
    silver = [c for c in cat if c["layer"] == "silver"][0]
    assert cert["id"] in silver["derived_from"]
    lin = client.get(f"/api/lake/lineage/{silver['id']}", headers=alice["headers"]).json()
    assert lin["layer"] == "silver" and lin["derived_from"][0]["layer"] == "bronze" and lin["derived_from"][0]["sha256"] == d["sha256"]


def test_silver_estandarizado_sin_datos_personales(client, alice):
    from .test_resume import save
    client.get("/api/resume", headers=alice["headers"]); save(client, alice, 0)
    client.post("/api/education", json=edu_payload(nombre_estudios="Ingeniería de Sistemas"), headers=alice["headers"])
    client.post("/api/work", json=work_payload(), headers=alice["headers"])
    client.post("/api/lake/refresh-silver", headers=alice["headers"])
    uid = get_db().users.find_one({"email": alice["email"]})["_id"]
    rows = list(get_db().silver_records.find({"owner_id": uid}))
    assert len(rows) == 2
    blob = str(rows)
    for pii in ("1000000000", "Ana", "Prueba", "Calle 1", "3000000000", alice["email"], "rrhh@"):
        assert pii not in blob
    assert [r for r in rows if r["kind"] == "education"][0]["data"]["nombre_estudios"] == "INGENIERIA DE SISTEMAS"   # sin tildes, mayúsculas


def test_refresh_silver_es_idempotente_sin_duplicar(client, alice):
    client.post("/api/education", json=edu_payload(), headers=alice["headers"])
    client.post("/api/lake/refresh-silver", headers=alice["headers"])
    n1 = get_db().silver_records.count_documents({}); l1 = get_db().lake_objects.count_documents({"layer": "silver"})
    client.post("/api/lake/refresh-silver", headers=alice["headers"])
    assert get_db().silver_records.count_documents({}) == n1 and get_db().lake_objects.count_documents({"layer": "silver"}) == l1


def test_gold_sin_pii_y_con_supresion_k(client, make_user):
    from app.core.config import get_settings
    from app.modules.lake import service as lake
    db = get_db()
    db.silver_records.delete_many({}); db.gold_metrics.delete_many({})
    users = [make_user() for _ in range(6)]
    for i, u in enumerate(users):
        client.post("/api/education", json=edu_payload(modalidad="UN"), headers=u["headers"])
        if i == 0:
            client.post("/api/education", json=edu_payload(modalidad="DOC"), headers=u["headers"])   # solo 1 => debe suprimirse
        client.post("/api/lake/refresh-silver", headers=u["headers"])
    r = client.post("/api/lake/build-gold", headers={"X-Admin-Token": "test-admin"}).json()
    assert r["suppressed"] >= 1 and r["written"] >= 1
    g = client.get("/api/lake/gold", headers=users[0]["headers"]).json()
    dims = {(x["metric"], x["dimension"]): x["value"] for x in g}
    assert dims[("educacion_por_modalidad", "UN")] == 6
    assert ("educacion_por_modalidad", "DOC") not in dims                      # k-anonimato (k=5)
    assert all(x["value"] >= get_settings().gold_k_anonymity for x in g)
    blob = str(g) + str(list(db.gold_metrics.find({})))
    for u in users:
        assert u["email"] not in blob
    assert "user_id" not in blob and "owner_id" not in blob
    # linaje de Gold: apunta a objetos Silver
    gl = db.lake_objects.find_one({"layer": "gold", "run_id": ObjectId(r["run_id"])})
    assert gl["derived_from"] and db.lake_objects.find_one({"_id": gl["derived_from"][0]})["layer"] == "silver"


def test_build_gold_requiere_token_admin(client, alice):
    assert client.post("/api/lake/build-gold").status_code == 403
    assert client.post("/api/lake/build-gold", headers={"X-Admin-Token": "mal"}).status_code == 403


def test_catalogo_solo_muestra_objetos_propios(client, alice, bob):
    rid = verified_education(client, alice)
    up(client, alice, rid)
    assert [c for c in client.get("/api/lake/catalog", headers=bob["headers"]).json() if c["kind"] == "certificate"] == []
    cert = [c for c in client.get("/api/lake/catalog", headers=alice["headers"]).json() if c["kind"] == "certificate"][0]
    assert client.get(f"/api/lake/lineage/{cert['id']}", headers=bob["headers"]).status_code == 404


def test_evidencia_de_verificacion_en_bronze_deduplicada(client, alice, bob):
    verified_education(client, alice)
    n = get_db().lake_objects.count_documents({"kind": "org_evidence"})
    verified_education(client, alice)            # misma respuesta cruda, mismo usuario => no se duplica
    assert get_db().lake_objects.count_documents({"kind": "org_evidence"}) == n


def test_validadores_mongo_segunda_barrera(client):
    from pymongo.errors import WriteError
    db = get_db()
    with pytest.raises(WriteError):
        db.documents.insert_one({"user_id": ObjectId(), "record_type": "work", "record_id": ObjectId(), "document_status": "ready",
                                 "authenticity": "validated", "sha256": "z", "size": 1})
    with pytest.raises(WriteError):
        db.documents.insert_one({"user_id": ObjectId(), "record_type": "work", "record_id": ObjectId(), "document_status": "ready",
                                 "authenticity": "not_validated", "sha256": "z", "size": 6 * 1024 * 1024})
    with pytest.raises(WriteError):
        db.work_records.insert_one({"user_id": ObjectId(), "resume_id": ObjectId(), "record_status": "verified", "organization_status": "pending"})
    with pytest.raises(WriteError):
        db.organizations.insert_one({"source": "otra", "official_id": "1", "name": "x", "status": "verified", "verified_at": __import__("datetime").datetime.now()})


def test_indices_clave_existen(client):
    db = get_db()
    def uniq(coll):
        return {tuple(k for k, _ in i["key"]) for i in db[coll].index_information().values() if i.get("unique")}
    assert ("source", "official_id") in uniq("organizations")
    assert ("user_id",) in uniq("resumes") and ("email",) in uniq("users") and ("token_hash",) in uniq("sessions")
    assert ("user_id", "idempotency_key") in uniq("documents")
    assert any(i.get("expireAfterSeconds") == 0 for i in db.sessions.index_information().values())
