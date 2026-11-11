"""Servidor Socrata SIMULADO (datos sintéticos) para pruebas de extremo a extremo. NO es una fuente oficial.
Usa las columnas reales de los datasets (confirmadas 2026-11-11) e interpreta las cláusulas SoQL que emite
el conector: igualdad, `in (...)`, `upper(col) like '...'` y `col != '...'` / `col IS NOT NULL` (ignoradas)."""
import json, re, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, unquote


def _snies(code, name, municipio, departamento):
    return {"c_digo_instituci_n": code, "nombre_instituci_n": name, "n_mero_identificaci_n": "900.000.000-1",
            "municipio_domicilio": municipio, "departamento_domicilio": departamento,
            "estado": "Activa en la Fecha de Actualizacion", "fecha_actualizacion": "2022-07-08"}


def _rues(nit, name):
    return {"nit": nit, "digito_verificacion": "1", "razon_social": name, "organizacion_juridica": "SOCIEDADES POR ACCIONES SIMPLIFICADAS SAS",
            "estado_matricula": "ACTIVA", "camara_comercio": "BOGOTA", "matricula": "100", "ultimo_ano_renovado": "2026"}


ROWS = {
    "n5yy-8nav": [_snies("1101", "UNIVERSIDAD SINTETICA DEL NORTE", "BOGOTA", "BOGOTA D.C."),
                  _snies("2202", "UNIVERSIDAD SINTETICA DEL NORTE", "MEDELLIN", "ANTIOQUIA")],
    "c82u-588k": [_rues("900000000", "EMPRESA SINTETICA SAS")],
}


def _like(pattern):
    return re.compile("^" + "".join(".*" if c == "%" else "." if c == "_" else re.escape(c) for c in pattern) + "$")


def _filter(rows, where):
    for col, val in re.findall(r"\b(\w+)='((?:[^']|'')*)'", where):
        rows = [r for r in rows if r.get(col) == val.replace("''", "'")]
    for col, vals in re.findall(r"\b(\w+) in \(([^)]*)\)", where):
        allowed = {v.strip().strip("'") for v in vals.split(",")}
        rows = [r for r in rows if r.get(col) in allowed]
    for col, pat in re.findall(r"upper\((\w+)\) like '((?:[^']|'')*)'", where):
        rx = _like(pat.replace("''", "'"))
        rows = [r for r in rows if rx.match(str(r.get(col, "")).upper())]
    return rows


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        u = urlparse(self.path)
        m = re.match(r"/resource/([a-z0-9-]+)\.json", u.path)
        rows = ROWS.get(m.group(1), []) if m else []
        rows = _filter(rows, unquote(parse_qs(u.query).get("$where", [""])[0]))
        body = json.dumps(rows).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def log_message(self, *a): pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 9999), H).serve_forever()
