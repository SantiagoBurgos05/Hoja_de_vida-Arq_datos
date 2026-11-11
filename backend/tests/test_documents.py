import pytest
from app.core import storage as st
from app.core.db import get_db
from .conftest import JPG, PDF, PNG
from .helpers import SNIES_ROWS, edu_payload, mock_source, reset_connectors, verified_education


@pytest.fixture(autouse=True)
def _clean():
    reset_connectors()
    yield
    reset_connectors()


def up(client, u, rid, data=PDF, name="cert.pdf", ctype="application/pdf", rt="education_higher", key=None):
    h = dict(u["headers"])
    if key:
        h["Idempotency-Key"] = key
    return client.post("/api/documents", data={"record_type": rt, "record_id": rid}, files={"file": (name, data, ctype)}, headers=h)


def test_no_se_permite_cargar_sin_entidad_verificada(client, alice):
    e = client.post("/api/education", json=edu_payload(), headers=alice["headers"]).json()
    r = up(client, alice, e["id"])
    assert r.status_code == 409 and r.json()["detail"]["code"] == "entidad_no_verificada"
    assert get_db().documents.count_documents({"record_id": __import__("bson").ObjectId(e["id"])}) == 0


def test_carga_y_recuperacion_en_sesion_futura_sin_recargar(client, alice):
    rid = verified_education(client, alice)
    r = up(client, alice, rid)
    assert r.status_code == 201
    d = r.json()
    assert d["document_status"] == "ready" and d["authenticity"] == "not_validated" and d["result"] == "created"
    assert client.get("/api/education", headers=alice["headers"]).json()[0]["record_status"] == "supported"
    client.post("/api/auth/logout", headers=alice["headers"])
    tok = client.post("/api/auth/login", json={"email": alice["email"], "password": alice["password"]}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}                         # otra sesión, sin volver a cargar nada
    lst = client.get(f"/api/documents?record_type=education_higher&record_id={rid}", headers=h).json()
    assert len(lst) == 1 and lst[0]["id"] == d["id"]
    dl = client.get(f"/api/documents/{d['id']}/download", headers=h)
    assert dl.status_code == 200 and dl.content == PDF
    assert dl.headers["x-content-type-options"] == "nosniff" and "attachment" in dl.headers["content-disposition"]
    assert dl.headers["content-type"] == "application/pdf"


def test_formatos_permitidos(client, alice):
    rid = verified_education(client, alice)
    assert up(client, alice, rid, PNG, "a.png", "image/png").status_code == 201
    assert up(client, alice, rid, JPG, "a.jpg", "image/jpeg").status_code == 201


@pytest.mark.parametrize("data,name,ctype,code", [
    (b"texto plano", "a.pdf", "application/pdf", 415),            # extensión PDF pero contenido no
    (b"MZ\x90\x00" + b"0" * 50, "a.exe", "application/octet-stream", 415),
    (PDF, "a.png", "image/png", 415),                              # firma real PDF, declarado PNG
    (b"", "vacio.pdf", "application/pdf", 422),
])
def test_rechaza_archivos_no_validos(client, alice, data, name, ctype, code):
    rid = verified_education(client, alice)
    assert up(client, alice, rid, data, name, ctype).status_code == code
    assert client.get(f"/api/documents?record_id={rid}", headers=alice["headers"]).json() == []


def test_limite_5mb(client, alice):
    rid = verified_education(client, alice)
    ok = b"%PDF-" + b"0" * (5 * 1024 * 1024 - 5)
    assert up(client, alice, rid, ok).status_code == 201
    big = b"%PDF-" + b"1" * (5 * 1024 * 1024 - 4)                  # 5 MB + 1 byte
    r = up(client, alice, rid, big)
    assert r.status_code == 413


def test_nombre_de_archivo_malicioso_se_sanea(client, alice):
    rid = verified_education(client, alice)
    d = up(client, alice, rid, PDF, '../../etc/passwd"; x=.pdf').json()
    assert "/" not in d["filename"] and '"' not in d["filename"] and d["filename"].endswith(".pdf")


def test_idempotencia_misma_clave_misma_operacion(client, alice):
    rid = verified_education(client, alice)
    a = up(client, alice, rid, PDF, key="clave-idem-0001")
    b = up(client, alice, rid, PDF, key="clave-idem-0001")
    assert a.status_code == 201 and b.status_code == 200 and b.json()["result"] == "idempotent" and a.json()["id"] == b.json()["id"]
    assert len(client.get(f"/api/documents?record_id={rid}", headers=alice["headers"]).json()) == 1
    c = up(client, alice, rid, PNG, "x.png", "image/png", key="clave-idem-0001")
    assert c.status_code == 409 and c.json()["detail"]["code"] == "idempotency_key_reutilizada"


def test_idempotencia_concurrente(client, alice):
    from concurrent.futures import ThreadPoolExecutor
    rid = verified_education(client, alice)
    with ThreadPoolExecutor(6) as ex:
        rs = list(ex.map(lambda _: up(client, alice, rid, PDF, key="clave-conc-0001"), range(6)))
    assert {r.status_code for r in rs} <= {200, 201} and len({r.json()["id"] for r in rs}) == 1
    assert len(client.get(f"/api/documents?record_id={rid}", headers=alice["headers"]).json()) == 1


def test_duplicado_de_contenido_en_mismo_registro(client, alice):
    rid = verified_education(client, alice)
    a = up(client, alice, rid, PDF)
    b = up(client, alice, rid, PDF)
    assert b.status_code == 200 and b.json()["result"] == "duplicate" and a.json()["id"] == b.json()["id"]


def test_fallo_de_almacenamiento_no_deja_ready(client, alice, monkeypatch):
    rid = verified_education(client, alice)
    real = st.get_storage()

    class Falla(st.LocalStorage):
        def put(self, *a, **k):
            raise st.StorageError("disco lleno")
    monkeypatch.setattr(st, "_storage", Falla(str(real.root)))
    r = up(client, alice, rid)
    assert r.status_code == 502 and r.json()["detail"]["code"] == "almacenamiento_fallo"
    docs = list(get_db().documents.find({"record_id": __import__("bson").ObjectId(rid)}))
    assert len(docs) == 1 and docs[0]["document_status"] == "rejected"
    assert client.get(f"/api/documents?record_id={rid}", headers=alice["headers"]).json() == []   # no aparece como cargado
    assert client.get("/api/education", headers=alice["headers"]).json()[0]["record_status"] == "declared"
    assert client.get(f"/api/documents/{docs[0]['_id']}/download", headers=alice["headers"]).status_code == 404
    monkeypatch.setattr(st, "_storage", real)
    again = up(client, alice, rid)                                 # reintento posible
    assert again.status_code == 201 and again.json()["document_status"] == "ready"


def test_escritura_truncada_se_detecta(client, alice, monkeypatch):
    rid = verified_education(client, alice)
    real = st.get_storage()

    class Trunca(st.LocalStorage):
        def put(self, key, data, ct):
            super().put(key, data[:10], ct)
    monkeypatch.setattr(st, "_storage", Trunca(str(real.root)))
    r = up(client, alice, rid)
    assert r.status_code == 502 and r.json()["detail"]["code"] == "almacenamiento_inconsistente"
    assert real.size(f"bronze/{get_db().users.find_one({'email': alice['email']})['_id']}/certificates/x.pdf") is None


def test_integridad_al_descargar(client, alice):
    rid = verified_education(client, alice)
    d = up(client, alice, rid).json()
    doc = get_db().documents.find_one({"sha256": d["sha256"], "record_id": __import__("bson").ObjectId(rid)})
    st.get_storage().put(doc["storage_key"], b"%PDF-adulterado", "application/pdf")
    r = client.get(f"/api/documents/{d['id']}/download", headers=alice["headers"])
    assert r.status_code == 502 and r.json()["detail"]["code"] == "integridad"


def test_aislamiento_documentos(client, alice, bob):
    rid = verified_education(client, alice)
    d = up(client, alice, rid).json()
    assert client.get(f"/api/documents/{d['id']}/download", headers=bob["headers"]).status_code == 404
    assert client.delete(f"/api/documents/{d['id']}", headers=bob["headers"]).status_code == 404
    assert client.get(f"/api/documents?record_id={rid}", headers=bob["headers"]).json() == []
    assert client.get(f"/api/documents/{d['id']}/download").status_code == 401
    # bob tampoco puede cargar sobre el registro de alice
    assert up(client, bob, rid).status_code == 404
    assert client.get(f"/api/documents/{d['id']}/download", headers=alice["headers"]).content == PDF


def test_borrado_coordinado(client, alice):
    rid = verified_education(client, alice)
    d = up(client, alice, rid).json()
    doc = get_db().documents.find_one({"sha256": d["sha256"], "record_id": __import__("bson").ObjectId(rid)})
    key, lo = doc["storage_key"], doc["lake_object_id"]
    assert st.get_storage().size(key) is not None
    assert client.delete(f"/api/documents/{d['id']}", headers=alice["headers"]).status_code == 204
    assert st.get_storage().size(key) is None                                     # objeto eliminado
    assert get_db().documents.find_one({"_id": doc["_id"]}) is None               # metadatos eliminados
    t = get_db().lake_objects.find_one({"_id": lo})
    assert t["deleted"] is True and t["storage_key"] is None                      # catálogo: tombstone
    assert client.get("/api/education", headers=alice["headers"]).json()[0]["record_status"] == "declared"


def test_borrado_pendiente_si_storage_falla_y_reintento(client, alice, monkeypatch):
    rid = verified_education(client, alice)
    d = up(client, alice, rid).json()
    real = st.get_storage()

    class NoBorra(st.LocalStorage):
        def delete(self, key):
            raise st.StorageError("caído")
    monkeypatch.setattr(st, "_storage", NoBorra(str(real.root)))
    r = client.delete(f"/api/documents/{d['id']}", headers=alice["headers"])
    assert r.status_code == 502 and r.json()["detail"]["code"] == "borrado_pendiente"
    assert get_db().documents.find_one({"sha256": d["sha256"], "record_id": __import__("bson").ObjectId(rid)})["document_status"] == "delete_pending"
    monkeypatch.setattr(st, "_storage", real)
    assert client.delete(f"/api/documents/{d['id']}", headers=alice["headers"]).status_code == 204


def test_borrar_registro_borra_sus_soportes(client, alice):
    rid = verified_education(client, alice)
    d = up(client, alice, rid).json()
    doc = get_db().documents.find_one({"sha256": d["sha256"], "record_id": __import__("bson").ObjectId(rid)})
    assert client.delete(f"/api/education/{rid}", headers=alice["headers"]).status_code == 204
    assert st.get_storage().size(doc["storage_key"]) is None
    assert get_db().documents.count_documents({"record_id": __import__("bson").ObjectId(rid)}) == 0


def test_cambiar_entidad_con_soportes_exige_borrarlos(client, alice):
    rid = verified_education(client, alice)
    up(client, alice, rid)
    r = client.post("/api/organizations/verify", json={"source": "snies", "official_id": "2202", "record_type": "education_higher", "record_id": rid}, headers=alice["headers"])
    assert r.status_code == 409 and r.json()["detail"]["code"] == "soportes_existentes"


def test_retencion_limpia_temporales(client, alice):
    from datetime import datetime, timedelta, timezone
    from app.modules.documents import service
    rid = verified_education(client, alice)
    from bson import ObjectId
    old = datetime.now(timezone.utc) - timedelta(days=31)
    key = f"bronze/x/certificates/temp-{ObjectId()}.pdf"
    st.get_storage().put(key, PDF, "application/pdf")
    get_db().documents.insert_one({"user_id": ObjectId(), "record_type": "work", "record_id": ObjectId(), "document_status": "rejected",
                                   "authenticity": "not_validated", "sha256": "x", "size": 10, "storage_key": key, "created_at": old})
    fresh = get_db().documents.insert_one({"user_id": ObjectId(), "record_type": "work", "record_id": ObjectId(), "document_status": "rejected",
                                           "authenticity": "not_validated", "sha256": "y", "size": 10, "storage_key": None, "created_at": datetime.now(timezone.utc)}).inserted_id
    out = service.cleanup_stale()
    assert out["removed"] >= 1 and st.get_storage().size(key) is None
    assert get_db().documents.find_one({"_id": fresh}) is not None


def test_soporte_de_educacion_basica_con_due(client, alice):
    mock_source("due", [{"a_o": "2025", "codigo_dane": "111001000001", "nombre_establecimiento": "COLEGIO SINTETICO", "municipio": "BOGOTA", "departamento": "BOGOTA D.C."}])
    resume = client.get("/api/resume", headers=alice["headers"]).json()
    r = client.post("/api/organizations/verify", json={"source": "due", "official_id": "111001000001", "record_type": "education_basic", "record_id": resume["id"]}, headers=alice["headers"])
    assert r.json()["organization_status"] == "verified"
    d = up(client, alice, resume["id"], PNG, "diploma.png", "image/png", rt="education_basic")
    assert d.status_code == 201
