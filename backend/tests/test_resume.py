import pytest
from .helpers import edu_payload, work_payload

PERSONAL = {"primer_apellido": "Prueba", "segundo_apellido": "Sintetica", "nombres": "Ana Maria", "tipo_documento": "CC",
            "numero_documento": "1000000000", "sexo": "F", "nacionalidad": "COL", "pais_nacionalidad": "Colombia",
            "nacimiento": {"fecha": "1999-05-20", "pais": "Colombia", "departamento": "Cundinamarca", "municipio": "Bogotá"},
            "correspondencia": {"pais": "Colombia", "departamento": "Cundinamarca", "municipio": "Bogotá", "direccion": "Calle 1 # 2-3", "telefono": "3000000000", "email": "ana@example.com"}}


def save(client, u, rev, **over):
    body = {"revision": rev, "personal": PERSONAL, "education_basic": {"ultimo_grado": 11, "titulo_obtenido": "Bachiller", "fecha_grado": {"mes": 12, "anio": 2016}},
            "languages": [{"idioma": "Inglés", "habla": "B", "lee": "MB", "escribe": "B"}]}
    body.update(over)
    return client.put("/api/resume", json=body, headers=u["headers"])


def test_persistencia_entre_sesiones(client, alice):
    r = client.get("/api/resume", headers=alice["headers"]).json()
    assert r["revision"] == 0
    s = save(client, alice, 0)
    assert s.status_code == 200 and s.json()["revision"] == 1
    e = client.post("/api/education", json=edu_payload(), headers=alice["headers"]).json()
    wk = client.post("/api/work", json=work_payload(), headers=alice["headers"]).json()
    client.post("/api/auth/logout", headers=alice["headers"])
    # nueva sesión
    login = client.post("/api/auth/login", json={"email": alice["email"], "password": alice["password"]}).json()
    h = {"Authorization": f"Bearer {login['token']}"}
    r2 = client.get("/api/resume", headers=h).json()
    assert r2["personal"]["nombres"] == "Ana Maria" and r2["languages"][0]["idioma"] == "Inglés" and r2["revision"] == 1
    assert [x["id"] for x in client.get("/api/education", headers=h).json()] == [e["id"]]
    assert [x["id"] for x in client.get("/api/work", headers=h).json()] == [wk["id"]]


def test_conflicto_de_revision_409_con_version_actual(client, alice):
    client.get("/api/resume", headers=alice["headers"])
    assert save(client, alice, 0).status_code == 200
    r = save(client, alice, 0)                       # otra pestaña con revisión vieja
    assert r.status_code == 409
    d = r.json()["detail"]
    assert d["code"] == "revision_obsoleta" and d["current"]["revision"] == 1


def test_guardado_concurrente_solo_uno_gana(client, alice):
    from concurrent.futures import ThreadPoolExecutor
    client.get("/api/resume", headers=alice["headers"])
    with ThreadPoolExecutor(8) as ex:
        codes = list(ex.map(lambda _: save(client, alice, 0).status_code, range(8)))
    assert codes.count(200) == 1 and codes.count(409) == 7


def test_cliente_no_puede_declararse_verificado(client, alice):
    r = client.post("/api/education", json={**edu_payload(), "organization_status": "verified"}, headers=alice["headers"])
    assert r.status_code == 422
    r = client.post("/api/work", json={**work_payload(), "record_status": "supported"}, headers=alice["headers"])
    assert r.status_code == 422


def test_estados_borrador_declarado(client, alice):
    d = client.post("/api/education", json={"modalidad": "TC"}, headers=alice["headers"]).json()
    assert d["record_status"] == "draft" and d["organization_status"] == "pending"
    assert client.post("/api/education", json=edu_payload(), headers=alice["headers"]).json()["record_status"] == "declared"


def test_validaciones(client, alice):
    assert client.post("/api/education", json={"modalidad": "XX"}, headers=alice["headers"]).status_code == 422
    assert client.put("/api/resume", json={"revision": 0, "personal": {}, "education_basic": {"ultimo_grado": 12}, "languages": []}, headers=alice["headers"]).status_code == 422
    bad_lang = {"revision": 0, "personal": {}, "education_basic": {}, "languages": [{"idioma": "Francés", "habla": "Z", "lee": "B", "escribe": "B"}]}
    assert client.put("/api/resume", json=bad_lang, headers=alice["headers"]).status_code == 422


def test_aislamiento_entre_usuarios(client, alice, bob):
    client.get("/api/resume", headers=alice["headers"])
    save(client, alice, 0)
    e = client.post("/api/education", json=edu_payload(), headers=alice["headers"]).json()
    w = client.post("/api/work", json=work_payload(), headers=alice["headers"]).json()
    # bob ve su propia hoja vacía y ninguna lista de alice
    rb = client.get("/api/resume", headers=bob["headers"]).json()
    assert rb["personal"] == {} and client.get("/api/education", headers=bob["headers"]).json() == []
    # y no puede leer/modificar/borrar recursos ajenos: 404 (indistinguible de inexistente)
    assert client.put(f"/api/education/{e['id']}", json=edu_payload(), headers=bob["headers"]).status_code == 404
    assert client.delete(f"/api/education/{e['id']}", headers=bob["headers"]).status_code == 404
    assert client.put(f"/api/work/{w['id']}", json=work_payload(), headers=bob["headers"]).status_code == 404
    assert client.delete(f"/api/work/{w['id']}", headers=bob["headers"]).status_code == 404
    assert client.put(f"/api/education/no-es-un-id", json=edu_payload(), headers=bob["headers"]).status_code == 404
    # el registro de alice sigue intacto
    assert len(client.get("/api/education", headers=alice["headers"]).json()) == 1


def test_actualizar_con_revision_obsoleta(client, alice):
    e = client.post("/api/education", json=edu_payload(), headers=alice["headers"]).json()
    ok = client.put(f"/api/education/{e['id']}", json={**edu_payload(nombre_estudios="Otro"), "revision": 0}, headers=alice["headers"])
    assert ok.status_code == 200 and ok.json()["revision"] == 1
    old = client.put(f"/api/education/{e['id']}", json={**edu_payload(), "revision": 0}, headers=alice["headers"])
    assert old.status_code == 409


def test_resumen_de_experiencia_endpoint(client, alice):
    client.post("/api/work", json=work_payload(fecha_ingreso="2020-01-01", fecha_retiro="2020-12-31"), headers=alice["headers"])
    s = client.get("/api/resume/experience-summary", headers=alice["headers"]).json()
    assert s["empleado_privado"]["dias"] == 366 and s["total"]["anios"] == 1
