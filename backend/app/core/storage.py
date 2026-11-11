"""Adaptador de almacenamiento privado. El navegador nunca accede directo: siempre vía API.

- LocalStorage: disco (desarrollo y pruebas).
- SupabaseStorage: Supabase Storage (bucket PRIVADO) por REST con service key (solo backend).
  AVISO: SupabaseStorage está implementado según la API REST documentada pero NO fue probado
  contra un proyecto real (sin acceso desde el entorno de desarrollo). Ver docs/estado.md.
"""
from __future__ import annotations
import os
import shutil
from pathlib import Path
import httpx
from urllib.parse import urlparse
from .config import get_settings


class StorageError(Exception):
    pass


class Storage:
    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def get(self, key: str) -> bytes: ...
    def size(self, key: str) -> int | None: ...
    def delete(self, key: str) -> None: ...


class LocalStorage(Storage):
    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _p(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if not str(p).startswith(str(self.root)):
            raise StorageError("Ruta inválida")
        return p

    def put(self, key, data, content_type):
        p = self._p(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".part")
        tmp.write_bytes(data)
        os.replace(tmp, p)

    def get(self, key):
        p = self._p(key)
        if not p.exists():
            raise StorageError("No existe")
        return p.read_bytes()

    def size(self, key):
        p = self._p(key)
        return p.stat().st_size if p.exists() else None

    def delete(self, key):
        p = self._p(key)
        if p.exists():
            p.unlink()


class SupabaseStorage(Storage):
    def __init__(self, url: str, key: str, bucket: str, transport: httpx.BaseTransport | None = None):
        # Solo esquema + host: si se pega la URL de la Data API (…/rest/v1/), se ignora la ruta.
        u = urlparse(url.strip())
        self.base = f"{u.scheme}://{u.netloc}/storage/v1"
        self.h = {"Authorization": f"Bearer {key}", "apikey": key}
        self.bucket, self.transport = bucket, transport

    def _c(self):
        return httpx.Client(timeout=20, transport=self.transport, headers=self.h)

    def put(self, key, data, content_type):
        with self._c() as c:
            r = c.post(f"{self.base}/object/{self.bucket}/{key}", content=data,
                       headers={"Content-Type": content_type, "x-upsert": "true"})
        if r.status_code not in (200, 201):
            raise StorageError(f"Supabase put HTTP {r.status_code}")

    def get(self, key):
        with self._c() as c:
            r = c.get(f"{self.base}/object/authenticated/{self.bucket}/{key}")
        if r.status_code != 200:
            raise StorageError(f"Supabase get HTTP {r.status_code}")
        return r.content

    def size(self, key):
        with self._c() as c:
            r = c.head(f"{self.base}/object/authenticated/{self.bucket}/{key}")
        if r.status_code != 200:
            return None
        return int(r.headers.get("content-length", "0"))

    def delete(self, key):
        with self._c() as c:
            r = c.delete(f"{self.base}/object/{self.bucket}/{key}")
        if r.status_code not in (200, 204, 404):
            raise StorageError(f"Supabase delete HTTP {r.status_code}")


_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        s = get_settings()
        if s.storage_backend == "supabase":
            _storage = SupabaseStorage(s.supabase_url, s.supabase_service_key, s.supabase_bucket)
        else:
            _storage = LocalStorage(s.local_storage_dir)
    return _storage


def set_storage(s: Storage | None) -> None:
    global _storage
    _storage = s
