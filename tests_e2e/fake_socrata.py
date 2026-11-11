"""Servidor Socrata SIMULADO (datos sintéticos) para pruebas de extremo a extremo. NO es una fuente oficial.
Usa las columnas reales del dataset SNIES n5yy-8nav (confirmadas 2026-11-10) e interpreta el LIKE de SoQL."""
import json, re, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, unquote


def _row(code, name, municipio, departamento):
    return {"c_digo_instituci_n": code, "nombre_instituci_n": name, "n_mero_identificaci_n": "900.000.000-1",
            "municipio_domicilio": municipio, "departamento_domicilio": departamento,
            "estado": "Activa en la Fecha de Actualizacion", "fecha_actualizacion": "2022-07-08"}


ROWS = {
    "n5yy-8nav": [_row("1101", "UNIVERSIDAD SINTETICA DEL NORTE", "BOGOTA", "BOGOTA D.C."),
                  _row("2202", "UNIVERSIDAD SINTETICA DEL NORTE", "MEDELLIN", "ANTIOQUIA")],
}


def _like(pattern):
    return re.compile("^" + "".join(".*" if c == "%" else "." if c == "_" else re.escape(c) for c in pattern) + "$")


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        u = urlparse(self.path)
        m = re.match(r"/resource/([a-z0-9-]+)\.json", u.path)
        rows = ROWS.get(m.group(1), []) if m else []
        where = unquote(parse_qs(u.query).get("$where", [""])[0])
        idm = re.search(r"c_digo_instituci_n='([^']*)'", where)
        if idm:
            rows = [r for r in rows if r["c_digo_instituci_n"] == idm.group(1)]
        nm = re.search(r"upper\(nombre_instituci_n\) like '((?:[^']|'')*)'", where)
        if nm:
            rx = _like(nm.group(1).replace("''", "'"))
            rows = [r for r in rows if rx.match(r["nombre_instituci_n"].upper())]
        body = json.dumps(rows).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def log_message(self, *a): pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 9999), H).serve_forever()
