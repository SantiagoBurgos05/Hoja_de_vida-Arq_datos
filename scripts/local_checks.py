"""Comprobaciones locales reproducibles. Solo servicios y datos de prueba propios.

e2e: MongoDB externo, base aleatoria; inicia API, fuente simulada y Vite temporalmente.
docker: construye las imágenes y prueba un volumen nuevo con el usuario de la API.
Un requisito ausente o una comprobación fallida devuelve un código distinto de cero.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen
import uuid

ROOT = Path(__file__).resolve().parents[1]


def command(args):
    executable = shutil.which(args[0])
    if not executable:
        raise RuntimeError(f"Comando no disponible: {args[0]}")
    return [executable, *args[1:]]


def run(args, *, cwd=ROOT, env=None, timeout=600):
    subprocess.run(command(args), cwd=cwd, env=env, check=True, timeout=timeout)


def free_ports(count):
    with ExitStack() as stack:
        sockets = [stack.enter_context(socket.socket()) for _ in range(count)]
        for sock in sockets:
            sock.bind(("127.0.0.1", 0))
        return [sock.getsockname()[1] for sock in sockets]


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def start(stack, args, cwd, env, log):
    output = stack.enter_context(log.open("w", encoding="utf-8"))
    process = subprocess.Popen(command(args), cwd=cwd, env=env, stdout=output,
                               stderr=subprocess.STDOUT,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    stack.callback(stop, process)
    return process


def ready(process, url, log):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Servicio terminado al iniciar; consulte {log}")
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.2)
    raise RuntimeError(f"Servicio no disponible: {url}; consulte {log}")


def e2e():
    from pymongo import MongoClient

    output = Path(os.getenv("E2E_OUT", ROOT / ".local-checks" / "e2e")).resolve()
    output.mkdir(parents=True, exist_ok=True)
    uri = os.getenv("TEST_MONGO_URI", "mongodb://127.0.0.1:27017")
    database = "hv_e2e_" + uuid.uuid4().hex
    api_port, source_port, web_port = free_ports(3)
    api_url, web_url = f"http://127.0.0.1:{api_port}", f"http://127.0.0.1:{web_port}"
    with MongoClient(uri, serverSelectionTimeoutMS=5000) as mongo:
        mongo.admin.command("ping")
        with ExitStack() as stack:
            # La base es nueva en cada ejecución; nunca se borra MONGO_DB del usuario.
            stack.callback(mongo.drop_database, database)
            storage = stack.enter_context(tempfile.TemporaryDirectory(prefix="storage-", dir=output))
            env = dict(os.environ, PYTHONUTF8="1", PYTHONUNBUFFERED="1",
                       MONGO_URI=uri, MONGO_DB=database, STORAGE_BACKEND="local",
                       LOCAL_STORAGE_DIR=storage, CORS_ORIGINS=web_url,
                       ALLOWED_CONNECTOR_HOSTS="127.0.0.1", ADMIN_TOKEN="",
                       SOCRATA_URL_TEMPLATE=f"http://127.0.0.1:{source_port}/resource/{{dataset}}.json",
                       VITE_API_URL=api_url, E2E_WEB=web_url, E2E_OUT=str(output))
            # Compilación aislada: no deja frontend/dist apuntando a una API de prueba ya cerrada.
            build = stack.enter_context(tempfile.TemporaryDirectory(prefix="frontend-", dir=output))
            run(["npm", "run", "build", "--", "--outDir", build], cwd=ROOT / "frontend", env=env)
            services = [
                ([sys.executable, "tests_e2e/fake_socrata.py", str(source_port)], ROOT,
                 f"http://127.0.0.1:{source_port}/resource/n5yy-8nav.json", "source.log"),
                ([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(api_port)],
                 ROOT / "backend", api_url + "/api/health", "api.log"),
                (["node", "node_modules/vite/bin/vite.js", "preview", "--host", "127.0.0.1", "--strictPort",
                  "--port", str(web_port), "--outDir", build], ROOT / "frontend", web_url, "web.log"),
            ]
            for args, cwd, url, name in services:
                log = output / name
                process = start(stack, args, cwd, env, log)
                ready(process, url, log)
            run([sys.executable, "tests_e2e/e2e.py"], env=env, timeout=180)
    print("E2E local completo; fuente SIMULADA. Servicios y base de prueba limpiados.", flush=True)


def docker():
    # Fallar antes de crear recursos si el motor no está disponible o no es accesible.
    run(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=30)
    project = "hvcheck-" + uuid.uuid4().hex[:12]
    compose = ["docker", "compose", "--project-name", project, "--file", str(ROOT / "docker-compose.yml")]
    # Evitar que el .env del usuario aporte secretos de producción a esta prueba.
    env = dict(os.environ, ADMIN_TOKEN="")
    try:
        run([*compose, "build", "api", "web"], env=env, timeout=900)
        run([*compose, "up", "-d", "--wait", "--wait-timeout", "90", "mongo"], env=env, timeout=150)
        probe = "from app.core.storage import get_storage; import os; assert os.getuid()!=0; s=get_storage(); "
        write = probe + "s.put('smoke/probe.bin',b'sintetico','application/octet-stream'); assert s.get('smoke/probe.bin')==b'sintetico'; print('Escritura OK; uid=',os.getuid())"
        read = probe + "assert s.get('smoke/probe.bin')==b'sintetico'; s.delete('smoke/probe.bin'); print('Persistencia y borrado OK en un segundo contenedor')"
        for code in (write, read):
            run([*compose, "run", "--rm", "--no-deps", "api", "python", "-c", code], env=env, timeout=60)
        print("Imágenes construidas; volumen persistente y escribible sin root.", flush=True)
    finally:
        # Solo recursos del nombre aleatorio generado arriba; no toca el Compose habitual.
        run([*compose, "down", "--volumes", "--remove-orphans"], env=env, timeout=90)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("check", choices=("e2e", "docker"))
    args = parser.parse_args()
    try:
        {"e2e": e2e, "docker": docker}[args.check]()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"FALLA {args.check}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
