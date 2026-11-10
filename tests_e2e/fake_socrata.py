"""Servidor Socrata SIMULADO (datos sintéticos) para pruebas de extremo a extremo. NO es una fuente oficial."""
import json, re, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, unquote

ROWS = {
    "n5yy-8nav": [  # SNIES (campos supuestos)
        {"codigo_institucion": "1101", "nombre_institucion": "UNIVERSIDAD SINTETICA DEL NORTE", "municipio_domicilio": "BOGOTA", "departamento_domicilio": "BOGOTA D.C.", "estado_institucion": "Activa"},
        {"codigo_institucion": "2202", "nombre_institucion": "UNIVERSIDAD SINTETICA DEL NORTE", "municipio_domicilio": "MEDELLIN", "departamento_domicilio": "ANTIOQUIA", "estado_institucion": "Activa"},
    ],
}

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        u = urlparse(self.path)
        m = re.match(r"/resource/([a-z0-9-]+)\.json", u.path)
        rows = ROWS.get(m.group(1), []) if m else []
        where = unquote(parse_qs(u.query).get("$where", [""])[0])
        idm = re.search(r"codigo_institucion='([^']*)'", where)
        if idm:
            rows = [r for r in rows if r["codigo_institucion"] == idm.group(1)]
        nm = re.search(r"like upper\('%(.*?)%'\)", where)
        if nm:
            rows = [r for r in rows if nm.group(1).upper() in r["nombre_institucion"]]
        body = json.dumps(rows).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass

if __name__ == "__main__":
    HTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 9999), H).serve_forever()
