from app.core.db import get_db
from app.core.security import token_hash


def test_registro_login_me(client):
    c = client
    assert c.post("/api/auth/register", json={"email": "Ana@Example.com", "password": "clave-sintetica-123"}).status_code == 201
    r = c.post("/api/auth/login", json={"email": "ana@example.com", "password": "clave-sintetica-123"})
    assert r.status_code == 200
    h = {"Authorization": f"Bearer {r.json()['token']}"}
    assert c.get("/api/auth/me", headers=h).json()["email"] == "ana@example.com"


def test_contrasena_argon2id_y_token_hasheado(client, alice):
    u = get_db().users.find_one({"email": alice["email"]})
    assert u["password_hash"].startswith("$argon2id$")
    assert "clave-sintetica" not in str(u)
    tok = alice["headers"]["Authorization"][7:]
    assert get_db().sessions.find_one({"token_hash": token_hash(tok)})
    assert get_db().sessions.find_one({"token_hash": tok}) is None   # el token en claro no se guarda


def test_registro_duplicado_no_revela(client, alice):
    r = client.post("/api/auth/register", json={"email": alice["email"], "password": "otra-clave-12345"})
    assert r.status_code == 409 and "existe" not in r.text.lower()


def test_contrasena_corta_rechazada(client):
    assert client.post("/api/auth/register", json={"email": "x@example.com", "password": "corta"}).status_code == 422


def test_credenciales_malas_y_limite_de_intentos(client, alice):
    for _ in range(5):
        assert client.post("/api/auth/login", json={"email": alice["email"], "password": "incorrecta-12345"}).status_code == 401
    # sexto intento (aun con la clave correcta) queda bloqueado por la ventana
    assert client.post("/api/auth/login", json={"email": alice["email"], "password": alice["password"]}).status_code == 429


def test_sin_token_401_y_logout_invalida(client, make_user):
    u = make_user()
    assert client.get("/api/resume").status_code == 401
    assert client.get("/api/resume", headers={"Authorization": "Bearer inventado"}).status_code == 401
    assert client.post("/api/auth/logout", headers=u["headers"]).status_code == 204
    assert client.get("/api/resume", headers=u["headers"]).status_code == 401


def test_sesion_vencida(client, make_user):
    from datetime import datetime, timedelta, timezone
    u = make_user()
    get_db().sessions.update_many({}, {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)}})
    assert client.get("/api/resume", headers=u["headers"]).status_code == 401
