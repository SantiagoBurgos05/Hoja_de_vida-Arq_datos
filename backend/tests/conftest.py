"""Pruebas contra un MongoDB REAL (TEST_MONGO_URI). Base de datos desechable por sesión de pruebas."""
from __future__ import annotations
import os
import shutil
import tempfile
import uuid
import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

TEST_URI = os.getenv("TEST_MONGO_URI", "mongodb://127.0.0.1:27017")   # mismo valor por defecto que README, CI y E2E


@pytest.fixture(scope="session")
def tmp_storage():
    d = tempfile.mkdtemp(prefix="hv-storage-")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(scope="session")
def client(tmp_storage):
    from app.core import config, db as dbmod, storage
    name = f"hv_test_{uuid.uuid4().hex[:8]}"
    config.set_settings(config.Settings(mongo_uri=TEST_URI, mongo_db=name, local_storage_dir=tmp_storage,
                                        admin_token="test-admin", login_max_attempts=5,
                                        # las pruebas crean cientos de usuarios desde la misma IP: límites altos por defecto;
                                        # test_limites.py los baja para comprobarlos
                                        rate_register=(100000, 3600), rate_lookup=(100000, 600), rate_upload=(100000, 3600)))
    storage.set_storage(None)
    dbmod.close_client()
    from app.main import create_app
    with TestClient(create_app()) as c:
        yield c
    MongoClient(TEST_URI).drop_database(name)
    dbmod.close_client()


def _user(client, email=None):
    email = email or f"u{uuid.uuid4().hex[:8]}@example.com"
    pw = "clave-sintetica-123"
    assert client.post("/api/auth/register", json={"email": email, "password": pw}).status_code == 201
    r = client.post("/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200
    return {"email": email, "password": pw, "headers": {"Authorization": f"Bearer {r.json()['token']}"}}


@pytest.fixture
def make_user(client):
    return lambda email=None: _user(client, email)


@pytest.fixture
def alice(make_user):
    return make_user()


@pytest.fixture
def bob(make_user):
    return make_user()


# --- datos sintéticos -------------------------------------------------------------
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n" + b"sintetico" * 20
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
