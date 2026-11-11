"""Adaptador SupabaseStorage contra un servidor simulado (la prueba en vivo es scripts/check_supabase.py)."""
import httpx
import pytest
from app.core.storage import StorageError, SupabaseStorage


def fake():
    store, seen = {}, []

    def handler(req: httpx.Request):
        seen.append((req.method, req.url.path, req.headers.get("authorization"), req.headers.get("apikey")))
        p = req.url.path
        for prefix in ("/storage/v1/object/authenticated/b/", "/storage/v1/object/b/"):
            if p.startswith(prefix):
                k = p[len(prefix):]
                break
        else:
            return httpx.Response(404, json={"code": "PGRST125"})
        if req.method == "POST":
            store[k] = req.content
            return httpx.Response(200)
        if req.method == "DELETE":
            store.pop(k, None)
            return httpx.Response(200)
        if k not in store:
            return httpx.Response(400)
        if req.method == "HEAD":
            return httpx.Response(200, headers={"content-length": str(len(store[k]))})
        return httpx.Response(200, content=store[k])
    return httpx.MockTransport(handler), store, seen


@pytest.mark.parametrize("url", ["https://p.supabase.co", "https://p.supabase.co/", "https://p.supabase.co/rest/v1/"])
def test_url_de_proyecto_normalizada(url):
    tr, store, seen = fake()
    s = SupabaseStorage(url, "k", "b", transport=tr)
    s.put("x/a.pdf", b"%PDF-1", "application/pdf")
    assert seen[0][1] == "/storage/v1/object/b/x/a.pdf" and store["x/a.pdf"] == b"%PDF-1"


def test_ciclo_completo_y_cabeceras():
    tr, store, seen = fake()
    s = SupabaseStorage("https://p.supabase.co", "clave", "b", transport=tr)
    s.put("k.pdf", b"abc", "application/pdf")
    assert s.size("k.pdf") == 3 and s.get("k.pdf") == b"abc"
    s.delete("k.pdf")
    assert s.size("k.pdf") is None
    with pytest.raises(StorageError):
        s.get("k.pdf")
    assert all(a == "Bearer clave" and k == "clave" for _, _, a, k in seen)


def test_origenes_cors_normalizados():
    from app.core.config import _origins
    assert _origins("https://SantiagoBurgos05.github.io") == ["https://santiagoburgos05.github.io"]
    assert _origins(" https://Usuario.github.io/repo/ , http://localhost:5173 ") == ["https://usuario.github.io", "http://localhost:5173"]
    assert _origins("") == []
