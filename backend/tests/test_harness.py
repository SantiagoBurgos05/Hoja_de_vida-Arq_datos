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
    monkeypatch.setattr(hz, "head", lambda: "aaa")
    e = {"check": {"ok": True, "head": "aaa"}}
    assert hz.fresh(e)
    monkeypatch.setattr(hz, "head", lambda: "bbb")
    assert not hz.fresh(e)


def test_no_se_cierra_sin_revision_ok(hz, monkeypatch):
    class A: task = "T-001"; verdict = "ok"; reviewer = "revision"; notes = ""
    s = {"T-001": {"status": "review", "fails": 0, "check": {"ok": True, "head": "x"}}}
    hz.save(s); monkeypatch.setattr(hz, "head", lambda: "x")
    with pytest.raises(SystemExit):
        hz.cmd_close(A)
    s["T-001"]["review"] = {"verdict": "changes", "head": "x"}; hz.save(s)
    with pytest.raises(SystemExit):
        hz.cmd_close(A)
