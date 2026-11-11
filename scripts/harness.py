#!/usr/bin/env python3
"""Harness de desarrollo (One-Person Company).

Máquina de estados por tarea: pending -> ready -> running -> checking -> review -> accepted ; blocked tras 3 fallos.
Un commit nuevo (HEAD distinto) o cualquier cambio en el árbol de trabajo (huella del contenido) invalida checks y revisión.
Comandos: validate | status | start T | check T | review T --verdict ok|changes --reviewer R --notes N | close T
Solo se ejecutan comandos de un registro cerrado (no hay ejecución arbitraria desde tasks.json).
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
H = ROOT / "harness"
STATE = H / "state.json"
EVID = H / "evidence"
PY = os.getenv("HARNESS_PYTHON", sys.executable)
MAX_FAILS = 3

# Registro cerrado de checks permitidos
CHECKS = {
    "validate": None,  # interno
    "npm:test": (["npm", "test"], ROOT / "frontend"),
    "npm:build": (["npm", "run", "build"], ROOT / "frontend"),
    "local:e2e": ([PY, "scripts/local_checks.py", "e2e"], ROOT),
    "docker:smoke": ([PY, "scripts/local_checks.py", "docker"], ROOT),
}


def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def tasks(): return {t["id"]: t for t in load(H / "tasks.json")["tasks"]}
def state():
    return load(STATE) if STATE.exists() else {}
def save(s): STATE.write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")
def head():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "sin-git"
def dirty():
    try:
        return bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout.strip())
    except Exception:
        return False

# El propio harness escribe estos archivos al registrar checks y revisiones: no forman parte del contenido evaluado.
TREE_EXCLUDE = ("harness/state.json", "harness/evidence/")


def _git(*args) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def tree():
    """Huella SHA-256 del contenido evaluado: HEAD + cambios sin commit (staged y unstaged) + archivos no versionados.
    Con árbol limpio equivale a HEAD; con cambios, cualquier edición posterior produce otra huella."""
    try:
        h = hashlib.sha256(_git("rev-parse", "HEAD"))
        excl = [f":(exclude){p}" for p in TREE_EXCLUDE]
        h.update(_git("diff", "HEAD", "--binary", "--", ".", *excl))
        for f in sorted(_git("ls-files", "--others", "--exclude-standard", "-z").decode("utf-8", "replace").split("\0")):
            if not f or f.startswith(TREE_EXCLUDE):
                continue
            h.update(f.encode("utf-8"))
            try:
                h.update(hashlib.sha256((ROOT / f).read_bytes()).digest())
            except OSError:
                h.update(b"<ilegible>")
        return h.hexdigest()
    except Exception:
        return "sin-git"


def entry(s, t):
    return s.setdefault(t, {"status": "pending", "fails": 0})


def refresh_ready(s):
    T = tasks()
    for tid, t in T.items():
        e = entry(s, tid)
        if e["status"] == "pending" and all(s.get(d, {}).get("status") == "accepted" for d in t["depends_on"]):
            e["status"] = "ready"


# ------------------------------------------------------------------ validate
def route_set_from_openapi() -> set[str]:
    code = ("import sys,json;sys.path.insert(0,'backend');from app.main import create_app;"
            "a=create_app();print(json.dumps([m.upper()+' '+p for p,v in a.openapi()['paths'].items() for m in v]))")
    out = subprocess.run([PY, "-c", code], cwd=ROOT, capture_output=True, text=True)
    if out.returncode:
        raise RuntimeError(out.stderr[-500:])
    return set(json.loads(out.stdout.strip().splitlines()[-1]))


def validate() -> list[str]:
    errs = []
    T, F = tasks(), {f["id"]: f for f in load(H / "features.json")["features"]}
    for t in T.values():
        for d in t["depends_on"]:
            if d not in T: errs.append(f"{t['id']}: dependencia inexistente {d}")
        for f in t["feature"]:
            if f not in F: errs.append(f"{t['id']}: funcionalidad inexistente {f}")
        if not t["acceptance"]: errs.append(f"{t['id']}: sin criterios de aceptación")
        for c in t["checks"]:
            if c != "validate" and not c.startswith("pytest:") and c not in CHECKS: errs.append(f"{t['id']}: check no permitido {c}")
            if c.startswith("pytest:") and not (ROOT / c.split(":", 1)[1]).exists(): errs.append(f"{t['id']}: archivo de prueba inexistente {c}")
    # ciclos
    seen, stack = set(), set()
    def dfs(n):
        if n in stack: errs.append(f"ciclo de dependencias en {n}"); return
        if n in seen: return
        seen.add(n); stack.add(n)
        for d in T[n]["depends_on"]:
            if d in T: dfs(d)
        stack.discard(n)
    for n in T: dfs(n)
    for f in F.values():
        for tp in f["tests"]:
            if not (ROOT / tp).exists(): errs.append(f"{f['id']}: prueba inexistente {tp}")
    # documentación vs código: endpoints
    declared = {e for f in F.values() for e in f["endpoints"]} | set(load(H / "features.json").get("extra_endpoints", []))
    try:
        actual = route_set_from_openapi()
        for e in sorted(actual - declared): errs.append(f"endpoint implementado sin documentar en features.json: {e}")
        for e in sorted(declared - actual): errs.append(f"endpoint documentado que no existe: {e}")
        doc = (ROOT / "docs" / "api.md").read_text(encoding="utf-8") if (ROOT / "docs" / "api.md").exists() else ""
        for e in sorted(actual):
            if e not in doc: errs.append(f"endpoint ausente en docs/api.md: {e}")
    except Exception as ex:
        errs.append(f"no se pudo inspeccionar la API: {ex}")
    # Los espacios de firma / RR.HH. no deben existir como campos de datos
    for f in ("backend/app/modules/resume/models.py", "backend/app/core/schemas_mongo.py"):
        if re.search(r"firma|rrhh|observaciones", (ROOT / f).read_text(encoding="utf-8"), re.I):
            errs.append(f"{f}: no debe haber campos de firma/RR.HH. (se dejan en blanco)")
    return errs


# ------------------------------------------------------------------ comandos
def run_check(c: str) -> tuple[bool, str]:
    if c == "validate":
        e = validate(); return (not e, "\n".join(e) or "validate ok")
    if c.startswith("pytest:"):
        r = subprocess.run([PY, "-m", "pytest", "-q", c.split(":", 1)[1].replace("backend/", "", 1)], cwd=ROOT / "backend", capture_output=True, text=True)
    else:
        cmd, cwd = CHECKS[c]
        # En Windows npm es npm.cmd, no un ejecutable llamado npm.
        executable = shutil.which(cmd[0])
        if not executable:
            return False, f"Comando no disponible: {cmd[0]}"
        r = subprocess.run([executable, *cmd[1:]], cwd=cwd, capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
    return r.returncode == 0, (r.stdout + r.stderr)[-1500:]


def cmd_start(a):
    s = state(); refresh_ready(s); T = tasks()
    if a.task not in T: sys.exit("tarea inexistente")
    e = entry(s, a.task)
    if e["status"] != "ready": sys.exit(f"{a.task} está en estado {e['status']}; debe estar ready (dependencias aceptadas)")
    e.update(status="running", started=time.strftime("%FT%T"), head=head(), allowed_paths=T[a.task]["allowed_paths"]); save(s)
    print(f"{a.task} en ejecución. Rutas permitidas: {', '.join(T[a.task]['allowed_paths'])}")


def cmd_check(a):
    s = state(); T = tasks(); e = entry(s, a.task)
    if e["status"] not in ("running", "checking", "review", "blocked"): sys.exit(f"estado inválido: {e['status']}")
    if e["status"] == "blocked": sys.exit("tarea bloqueada tras 3 fallos: replantear con la dirección")
    e["status"] = "checking"; results = {}
    for c in T[a.task]["checks"]:
        ok, out = run_check(c); results[c] = {"ok": ok, "tail": out[-400:]}
    allok = all(r["ok"] for r in results.values())
    ev = {"task": a.task, "head": head(), "tree": tree(), "dirty": dirty(), "at": time.strftime("%FT%T"), "results": results, "ok": allok}
    EVID.mkdir(exist_ok=True); (EVID / f"{a.task}-{int(time.time())}.json").write_text(json.dumps(ev, indent=2, ensure_ascii=False), encoding="utf-8")
    e["check"] = {"ok": allok, "head": ev["head"], "tree": ev["tree"]}; e.pop("review", None)
    if allok:
        e["status"] = "review"; e["fails"] = 0
    else:
        e["fails"] += 1; e["status"] = "blocked" if e["fails"] >= MAX_FAILS else "running"
    save(s)
    for c, r in results.items(): print(("OK  " if r["ok"] else "FALLA"), c)
    print("→", e["status"], "(evidencia en harness/evidence/)")
    sys.exit(0 if allok else 1)


def fresh(e):
    """Vigencia: mismo commit Y mismo contenido evaluado (un cambio sin commit también invalida)."""
    c = e.get("check", {})
    return bool(c.get("ok")) and c.get("head") == head() and c.get("tree") == tree()


def cmd_review(a):
    s = state(); e = entry(s, a.task)
    if e["status"] != "review": sys.exit(f"estado inválido: {e['status']} (se requiere review)")
    if not fresh(e): sys.exit("un commit o cambio nuevo invalidó los checks: ejecute check de nuevo")
    if a.reviewer == tasks()[a.task]["role"] or a.reviewer == e.get("developer"): sys.exit("el revisor debe ser un rol distinto al que desarrolló")
    e["review"] = {"verdict": a.verdict, "reviewer": a.reviewer, "notes": a.notes, "head": head(), "tree": tree(), "at": time.strftime("%FT%T")}
    if a.verdict != "ok": e["status"] = "running"
    save(s); print("revisión registrada:", a.verdict)


def cmd_close(a):
    s = state(); e = entry(s, a.task)
    if e["status"] != "review": sys.exit(f"estado inválido: {e['status']}")
    r = e.get("review")
    if not r or r["verdict"] != "ok": sys.exit("falta revisión con veredicto ok")
    if r["head"] != head() or r.get("tree") != tree() or not fresh(e): sys.exit("un commit o cambio nuevo invalidó checks/revisión")
    if dirty(): sys.exit("hay cambios sin commit: la aceptación debe quedar ligada a un commit definitivo")
    e["status"] = "accepted"; e["accepted_at"] = time.strftime("%FT%T"); e["accepted_head"] = head(); e["accepted_tree"] = tree(); refresh_ready(s); save(s)
    print(f"{a.task} aceptada por la dirección")


def cmd_status(_):
    s = state(); refresh_ready(s); save(s)
    for tid, t in tasks().items(): print(f"{tid:6} {entry(s, tid)['status']:9} {t['title']}")


def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate"); sub.add_parser("status")
    for n in ("start", "check", "close"): sub.add_parser(n).add_argument("task")
    r = sub.add_parser("review"); r.add_argument("task"); r.add_argument("--verdict", choices=["ok", "changes"], required=True); r.add_argument("--reviewer", required=True); r.add_argument("--notes", default="")
    a = p.parse_args()
    if a.cmd == "validate":
        e = validate(); print("\n".join(e) if e else "validate ok"); sys.exit(1 if e else 0)
    {"start": cmd_start, "check": cmd_check, "review": cmd_review, "close": cmd_close, "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    main()
