"""Conector genérico para datasets abiertos de datos.gov.co (API SODA/Socrata).

AVISO: los nombres de columna de `field_map` son SUPUESTOS no verificados contra los datasets
reales (el entorno de desarrollo no tenía acceso a datos.gov.co). Ajustar en docs/fuentes.md.
Las pruebas usan respuestas simuladas (httpx.MockTransport).
"""
from __future__ import annotations
import json
from urllib.parse import urlparse
import httpx
from ....core.config import get_settings
from .base import Candidate, Connector, ConnectorError



def _esc(v: str) -> str:
    return v.replace("'", "''")


class SocrataConnector(Connector):
    def __init__(self, source: str, kind: str, dataset: str, field_map: dict, transport: httpx.BaseTransport | None = None):
        self.source, self.kind, self.dataset, self.fm = source, kind, dataset, field_map
        self.transport = transport

    # --- red -----------------------------------------------------------------
    def _get(self, params: dict) -> tuple[list[dict], str]:
        s = get_settings()
        url = s.socrata_url_template.format(dataset=self.dataset)
        host = urlparse(url).hostname
        if host not in s.allowed_connector_hosts:
            raise ConnectorError(f"Host no permitido: {host}")
        try:
            with httpx.Client(timeout=s.connector_timeout_s, follow_redirects=False, transport=self.transport) as c:
                r = c.get(url, params=params, headers={"Accept": "application/json"})
        except httpx.HTTPError as e:
            raise ConnectorError(f"Fuente no disponible: {type(e).__name__}") from e
        if r.status_code != 200:
            raise ConnectorError(f"La fuente respondió HTTP {r.status_code}")
        if len(r.content) > s.connector_max_bytes:
            raise ConnectorError("Respuesta demasiado grande")
        try:
            data = r.json()
        except json.JSONDecodeError as e:
            raise ConnectorError("Respuesta no es JSON") from e
        if not isinstance(data, list):
            raise ConnectorError("Formato inesperado")
        return data, r.text

    def _to_candidate(self, row: dict) -> Candidate | None:
        oid = str(row.get(self.fm["id"], "")).strip()
        name = str(row.get(self.fm["name"], "")).strip()
        if not oid or not name:
            return None
        return Candidate(
            source=self.source, official_id=oid, name=name,
            municipio=str(row.get(self.fm.get("municipio", ""), "")).strip(),
            departamento=str(row.get(self.fm.get("departamento", ""), "")).strip(),
            estado_registral=str(row.get(self.fm.get("estado", ""), "")).strip(),
        )

    # --- API -----------------------------------------------------------------
    def search(self, query, municipio, official_id, limit=10):
        where = []
        if official_id:
            where.append(f"{self.fm['id']}='{_esc(official_id.strip())}'")
        if query:
            where.append(f"upper({self.fm['name']}) like upper('%{_esc(query.strip())}%')")
        if municipio and self.fm.get("municipio"):
            where.append(f"upper({self.fm['municipio']}) like upper('%{_esc(municipio.strip())}%')")
        if not where:
            return []
        rows, _ = self._get({"$where": " AND ".join(where), "$limit": str(min(limit, 20))})
        return [c for c in (self._to_candidate(r) for r in rows) if c]

    def get_by_official_id(self, official_id):
        rows, raw = self._get({"$where": f"{self.fm['id']}='{_esc(official_id.strip())}'", "$limit": "5"})
        cands = [c for c in (self._to_candidate(r) for r in rows) if c and c.official_id == official_id.strip()]
        return cands, {"raw": raw}
