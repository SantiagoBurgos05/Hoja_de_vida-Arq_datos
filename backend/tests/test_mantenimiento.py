"""Paso 4: mantenimiento operativo, cuota por usuario y límites de uso."""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from bson import ObjectId
from app.core import storage as st
from app.core.config import get_settings
from app.core.db import get_db
from .conftest import PDF, PNG
from .helpers import SNIES_ROWS, edu_payload, mock_source, reset_connectors, verified_education
from .test_documents import up

ADMIN = {"X-Admin-Token": "test-admin"}


@pytest.fixture(autouse=True)
def _clean():
    reset_connectors()
    yield
    reset_connectors()


@pytest.fixture
def settings_patch():
    """Cambia ajustes durante una prueba y los restaura al terminar."""
    s, old = get_settings(), {}

    def set_(**kw):
        for k, v in kw.items():
            old.setdefault(k, getattr(s, k))
            setattr(s, k, v)
    yield set_
    for k, v in old.items():
        setattr(s, k, v)


class FallaBorrado:
    """Storage que guarda y lee en el almacenamiento real pero falla al borrar."""
    def __init__(self, real):
        self.real = real

    def put(self, *a): return self.real.put(*a)
    def get(self, *a): return self.real.get(*a)
    def size(self, *a): return self.real.size(*a)
    def delete(self, *a): raise st.StorageError("caido")


# --------------------------------------------------------------- mantenimiento
def test_mantenimiento_exige_token_admin(client):
    assert client.post("/api/admin/maintenance").status_code == 403
    assert client.post("/api/admin/maintenance", headers={"X-Admin-Token": "otro"}).status_code == 403
    assert client.get("/api/admin/maintenance").status_code == 403


def test_mantenimiento_completa_borrado_pendiente(client, alice):
    rid = verified_education(client, alice)
    d = up(client, alice, rid).json()
    real = st.get_storage()
    key = get_db().documents.find_one({"_id": ObjectId(d["id"])})["storage_key"]
    st.set_storage(FallaBorrado(real))
    try:
        assert client.delete(f"/api/documents/{d['id']}", headers=alice["headers"]).status_code == 502
    finally:
        st.set_storage(real)
    assert get_db().documents.find_one({"_id": ObjectId(d["id"])})["document_status"] == "delete_pending"
    r = client.post("/api/admin/maintenance", headers=ADMIN)
    assert r.status_code == 200 and r.json()["results"]["retry_pending_deletes"]["completed"] >= 1
    assert get_db().documents.find_one({"_id": ObjectId(d["id"])}) is None and real.size(key) is None
    lo = get_db().lake_objects.find_one({"kind": "certificate", "source_ref.document_id": d["id"]})
    assert lo["deleted"] is True
    assert client.get("/api/education", headers=alice["headers"]).json()[0]["record_status"] == "declared"


def test_mantenimiento_expira_carga_interrumpida_y_libera_clave(client, alice):
    rid = verified_education(client, alice)
    uid = get_db().users.find_one({"email": alice["email"]})["_id"]
    key = f"bronze/{uid}/certificates/{ObjectId()}.pdf"
    st.get_storage().put(key, PDF, "application/pdf")
    old = datetime.now(timezone.utc) - timedelta(hours=3)
    doc_id = get_db().documents.insert_one({
        "user_id": uid, "record_type": "education_higher", "record_id": ObjectId(rid), "organization_id": None,
        "filename": "cert.pdf", "content_type": "application/pdf", "size": len(PDF), "sha256": "a" * 64, "storage_key": key,
        "document_status": "uploading", "authenticity": "not_validated", "idempotency_key": "clave-interrumpida-1",
        "lake_object_id": None, "created_at": old}).inserted_id
    r = client.post("/api/admin/maintenance", headers=ADMIN).json()
    assert r["results"]["expire_stale_uploads"]["expired"] >= 1
    d = get_db().documents.find_one({"_id": doc_id})
    assert d["document_status"] == "rejected" and "idempotency_key" not in d and st.get_storage().size(key) is None
    assert up(client, alice, rid, PDF, key="clave-interrumpida-1").status_code == 201     # la clave quedó libre


def test_mantenimiento_concilia_silver_y_construye_gold(client, alice):
    e = client.post("/api/education", json=edu_payload(), headers=alice["headers"]).json()
    get_db().education_records.delete_one({"_id": ObjectId(e["id"])})          # borrado fuera del servicio
    r = client.post("/api/admin/maintenance", headers=ADMIN).json()
    assert r["ok"] and r["results"]["reconcile_silver"]["removed"] >= 1
    assert get_db().silver_records.find_one({"source_id": e["id"]}) is None
    assert r["results"]["build_gold"]["ok"] and "run_id" in r["results"]["build_gold"]
    runs = client.get("/api/admin/maintenance", headers=ADMIN).json()
    assert runs[0]["id"] == r["id"] and runs[0]["trigger"] == "manual"


def test_un_paso_fallido_no_detiene_los_demas(client, monkeypatch):
    from app.modules.admin import service as adm

    def boom():
        raise RuntimeError("sin conexión")
    steps = [(n, boom if n == "cleanup_stale" else f) for n, f in adm.STEPS]
    monkeypatch.setattr(adm, "STEPS", steps)
    r = client.post("/api/admin/maintenance", headers=ADMIN)
    assert r.status_code == 500
    res = r.json()["results"]
    assert res["cleanup_stale"]["ok"] is False and "sin conexión" in res["cleanup_stale"]["error"]
    assert res["build_gold"]["ok"] is True and res["retry_pending_deletes"]["ok"] is True
    assert get_db().maintenance_runs.find_one({"_id": ObjectId(r.json()["id"])})["ok"] is False


def test_mantenimiento_por_linea_de_comandos(client, capsys):
    from app import maintenance
    assert maintenance.main() == 0
    assert '"trigger": "cli"' in capsys.readouterr().out


# ------------------------------------------------------------------- cuota
def test_cuota_de_almacenamiento_por_usuario(client, alice, settings_patch):
    rid = verified_education(client, alice)
    settings_patch(user_storage_quota_bytes=len(PDF) + 10)
    assert up(client, alice, rid, PDF).status_code == 201
    r = up(client, alice, rid, PNG, "x.png", "image/png")
    assert r.status_code == 413 and r.json()["detail"]["code"] == "cuota_excedida"
    assert up(client, alice, rid, PDF).status_code == 200                       # duplicado: no ocupa espacio nuevo
    u = client.get("/api/documents/usage", headers=alice["headers"]).json()
    assert u == {"used_bytes": len(PDF), "quota_bytes": len(PDF) + 10, "available_bytes": 10}


# ---------------------------------------------------------- límites de uso
def test_limite_de_registros_por_ip(client, settings_patch):
    settings_patch(trust_proxy=True, rate_register=(2, 3600))
    h = {"X-Forwarded-For": f"10.0.0.1, 203.0.113.{uuid.uuid4().int % 250}"}      # el proxy agrega la IP real al final
    codes = [client.post("/api/auth/register", json={"email": f"r{uuid.uuid4().hex[:8]}@example.com", "password": "clave-sintetica-123"},
                         headers=h).status_code for _ in range(3)]
    assert codes == [201, 201, 429]
    otra = {"X-Forwarded-For": "198.51.100.7"}
    assert client.post("/api/auth/register", json={"email": f"r{uuid.uuid4().hex[:8]}@example.com", "password": "clave-sintetica-123"},
                       headers=otra).status_code == 201


def test_sin_proxy_de_confianza_se_ignora_x_forwarded_for(client, settings_patch):
    from starlette.requests import Request
    from app.core.ratelimit import client_ip
    req = Request({"type": "http", "headers": [(b"x-forwarded-for", b"1.2.3.4")], "client": ("10.9.9.9", 1)})
    settings_patch(trust_proxy=False)
    assert client_ip(req) == "10.9.9.9"
    settings_patch(trust_proxy=True)
    assert client_ip(req) == "1.2.3.4"


def test_x_forwarded_for_falsificado_no_evade_limites(client, settings_patch):
    """El cliente puede escribir valores a la IZQUIERDA de X-Forwarded-For; el proxy agrega la IP real al final.
    Cambiar el valor falsificado no debe dar una IP nueva (antes evadía el límite de registro y el bloqueo de login)."""
    from starlette.requests import Request
    from app.core.ratelimit import client_ip
    settings_patch(trust_proxy=True, trusted_proxy_hops=1)
    real = "198.51.100.23"
    ips = {client_ip(Request({"type": "http", "headers": [(b"x-forwarded-for", f"6.6.6.{i}, {real}".encode())],
                                "client": ("10.0.0.1", 1)})) for i in range(5)}
    assert ips == {real}
    settings_patch(rate_register=(2, 3600))
    codes = [client.post("/api/auth/register", json={"email": f"f{uuid.uuid4().hex[:8]}@example.com", "password": "clave-sintetica-123"},
                         headers={"X-Forwarded-For": f"6.6.6.{i}, 192.0.2.77"}).status_code for i in range(3)]
    assert codes == [201, 201, 429]                                  # rotar el valor falsificado no ayuda


def test_bloqueo_de_login_no_se_evade_con_ip_falsificada(client, alice, settings_patch):
    settings_patch(trust_proxy=True, trusted_proxy_hops=1)
    bad = {"email": alice["email"], "password": "clave-equivocada-000"}
    codes = [client.post("/api/auth/login", json=bad, headers={"X-Forwarded-For": f"6.6.6.{i}, 192.0.2.88"}).status_code
             for i in range(6)]
    assert codes[:5] == [401] * 5 and codes[5] == 429


def test_limite_de_consultas_a_fuentes_por_usuario(client, alice, bob, settings_patch):
    mock_source("snies", SNIES_ROWS)
    settings_patch(rate_lookup=(2, 600))
    body = {"source": "snies", "query": "universidad"}
    codes = [client.post("/api/organizations/search", json=body, headers=alice["headers"]).status_code for _ in range(2)]
    v = client.post("/api/organizations/verify", json={"source": "snies", "official_id": "1101"}, headers=alice["headers"])
    assert codes == [200, 200] and v.status_code == 429 and v.json()["detail"]["code"] == "limite_de_uso"
    assert client.post("/api/organizations/search", json=body, headers=bob["headers"]).status_code == 200   # por usuario


def test_limite_de_cargas_por_usuario(client, alice, settings_patch):
    rid = verified_education(client, alice)
    settings_patch(rate_upload=(1, 3600))
    assert up(client, alice, rid, PDF).status_code == 201
    assert up(client, alice, rid, PNG, "x.png", "image/png").status_code == 429
