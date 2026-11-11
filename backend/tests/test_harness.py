import importlib.util, json, shutil
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def hz(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("harness", ROOT / "scripts" / "harness.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    shutil.copytree(ROOT / "harness", tmp_path / "harness", ignore=shutil.ignore_patterns("evidence", "state.json"))
    monkeypatch.setattr(m, "H", tmp_path / "harness"); monkeypatch.setattr(m, "STATE", tmp_path / "harness" / "state.json")
    monkeypatch.setattr(m, "EVID", tmp_path / "harness" / "evidence")
    return m


def test_catalogo_valido(hz):
    assert hz.validate() == []


def test_detecta_dependencia_y_ciclo(hz):
    t = json.loads((hz.H / "tasks.json").read_text())
    t["tasks"][0]["depends_on"] = ["T-009"]
    (hz.H / "tasks.json").write_text(json.dumps(t))
    assert any("ciclo" in e for e in hz.validate())


def test_detecta_endpoint_sin_documentar(hz):
    f = json.loads((hz.H / "features.json").read_text())
    f["features"][0]["endpoints"].pop()
    (hz.H / "features.json").write_text(json.dumps(f))
    assert any("sin documentar" in e for e in hz.validate())


def test_dependencias_y_maquina_de_estados(hz, monkeypatch):
    s = {}; hz.refresh_ready(s)
    assert s["T-001"]["status"] == "ready" and s["T-002"]["status"] == "pending"
    s["T-001"]["status"] = "accepted"; hz.refresh_ready(s)
    assert s["T-002"]["status"] == "ready" and s["T-003"]["status"] == "pending"


def test_commit_nuevo_invalida_checks(hz, monkeypatch):
    monkeypatch.setattr(hz, "head", lambda: "aaa"); monkeypatch.setattr(hz, "tree", lambda: "t1")
    e = {"check": {"ok": True, "head": "aaa", "tree": "t1"}}
    assert hz.fresh(e)
    monkeypatch.setattr(hz, "head", lambda: "bbb")
    assert not hz.fresh(e)


def test_cambio_sin_commit_invalida_checks(hz, monkeypatch):
    monkeypatch.setattr(hz, "head", lambda: "aaa"); monkeypatch.setattr(hz, "tree", lambda: "t1")
    e = {"check": {"ok": True, "head": "aaa", "tree": "t1"}}
    assert hz.fresh(e)
    monkeypatch.setattr(hz, "tree", lambda: "t2")                 # mismo HEAD, contenido editado
    assert not hz.fresh(e)
    assert not hz.fresh({"check": {"ok": True, "head": "aaa"}})   # evidencia antigua sin huella: no vigente


def test_huella_real_cambia_con_archivo_no_versionado(hz):
    if hz.tree() == "sin-git":
        pytest.skip("sin git")
    a = hz.tree()
    assert a == hz.tree()                                          # determinista
    p = hz.ROOT / "zz_harness_tmp_huella.txt"
    try:
        p.write_text("x", encoding="utf-8")
        assert hz.tree() != a
    finally:
        p.unlink(missing_ok=True)
    assert hz.tree() == a


def test_cierre_exige_arbol_limpio(hz, monkeypatch):
    class A: task = "T-001"; verdict = "ok"; reviewer = "revision"; notes = ""
    monkeypatch.setattr(hz, "head", lambda: "x"); monkeypatch.setattr(hz, "tree", lambda: "t")
    s = {"T-001": {"status": "review", "fails": 0, "check": {"ok": True, "head": "x", "tree": "t"},
                   "review": {"verdict": "ok", "head": "x", "tree": "t"}}}
    hz.save(s)
    monkeypatch.setattr(hz, "dirty", lambda: True)
    with pytest.raises(SystemExit):
        hz.cmd_close(A)
    monkeypatch.setattr(hz, "dirty", lambda: False)
    hz.cmd_close(A)
    assert hz.state()["T-001"]["status"] == "accepted"


def test_no_se_cierra_sin_revision_ok(hz, monkeypatch):
    class A: task = "T-001"; verdict = "ok"; reviewer = "revision"; notes = ""
    s = {"T-001": {"status": "review", "fails": 0, "check": {"ok": True, "head": "x"}}}
    hz.save(s); monkeypatch.setattr(hz, "head", lambda: "x")
    with pytest.raises(SystemExit):
        hz.cmd_close(A)
    s["T-001"]["review"] = {"verdict": "changes", "head": "x"}; hz.save(s)
    with pytest.raises(SystemExit):
        hz.cmd_close(A)


def test_check_resuelve_comando_de_windows(hz, monkeypatch):
    calls = []
    monkeypatch.setattr(hz.shutil, "which", lambda command: "C:/node/npm.cmd")
    def run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return hz.subprocess.CompletedProcess(cmd, 0, "8 passed", "")
    monkeypatch.setattr(hz.subprocess, "run", run)
    assert hz.run_check("npm:test") == (True, "8 passed")
    assert calls[0][0] == ["C:/node/npm.cmd", "test"]
    assert calls[0][1]["cwd"] == hz.ROOT / "frontend"


def test_check_sin_comando_no_se_presenta_como_aprobado(hz, monkeypatch):
    monkeypatch.setattr(hz.shutil, "which", lambda command: None)
    ok, message = hz.run_check("npm:test")
    assert not ok and "npm" in message
