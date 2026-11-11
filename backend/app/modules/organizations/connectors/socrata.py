"""Conector genérico para datasets abiertos de datos.gov.co (API SODA/Socrata).

Los nombres de columna se confirmaron contra los datasets reales el 2026-11-10 (ver docs/fuentes.md).
Las pruebas automatizadas usan respuestas grabadas/simuladas (httpx.MockTransport); la comprobación
en vivo es manual: `python scripts/check_sources.py`.
"""
from __future__ import annotations
import json
import re
import unicodedata
from urllib.parse import urlparse
import httpx
from ....core.config import get_settings
from .base import Candidate, Connector, ConnectorError


def _esc(v: str) -> str:
    return v.replace("'", "''")


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).upper()


def name_pattern(q: str) -> str:
    """Patrón LIKE tolerante a tildes: SoQL no tiene unaccent, así que cada vocal se vuelve el comodín `_`
    (POLITECNICO encuentra POLITÉCNICO). Los comodines del usuario se neutralizan. La selección final
    la hace la persona; la verificación sigue siendo por identificador oficial exacto."""
    q = re.sub(r"\s+", " ", _fold(q).replace("%", " ").replace("_", " ")).strip()
    return "%" + re.sub(r"[AEIOU]", "_", q) + "%"


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


class _Blank(dict):
    def __missing__(self, k):
        return ""


class SocrataConnector(Connector):
    """`field_map`: id, name, municipio, departamento y opcionalmente nit / estado (columnas).
    `estado_template`: texto del estado registral a partir de la fila (p. ej. "{estado} ({fecha_actualizacion})").
    `id_numeric`: la columna del identificador es numérica; un identificador no numérico no se consulta.
    `snapshot`: columna de corte (p. ej. año) cuando el dataset repite la entidad por periodo: se usa el corte
    más reciente en que aparece el identificador.
    `select`: columnas que se piden a la fuente. Limita la respuesta (y la evidencia guardada) a datos de la
    entidad: nunca se piden nombres ni documentos de representantes u otras personas.
    `base_where`: condición fija de toda consulta (p. ej. excluir personas naturales del registro mercantil).
    `active`: (columna, valor). Si un identificador devuelve varias filas y exactamente una está en ese estado,
    se usa esa (p. ej. matrícula ACTIVA frente a matrículas canceladas del mismo NIT).
    `nit_exact`: la columna NIT guarda solo dígitos: se consulta por igualdad (con y sin dígito de verificación)
    en lugar del prefiltro amplio, necesario en datasets grandes.
    `timeout_s`: tiempo máximo propio de la fuente (datasets de millones de filas).
    `id_len`: (mínimo, máximo) de dígitos del identificador; fuera de ese rango no se consulta (NIT de relleno como «1»)."""

    def __init__(self, source: str, kind: str, dataset: str, field_map: dict, transport: httpx.BaseTransport | None = None,
                 *, estado_template: str | None = None, id_numeric: bool = False, snapshot: str | None = None,
                 select: tuple[str, ...] | None = None, base_where: str | None = None, active: tuple[str, str] | None = None,
                 nit_exact: bool = False, timeout_s: float | None = None, id_len: tuple[int, int] | None = None):
        self.source, self.kind, self.dataset, self.fm = source, kind, dataset, field_map
        self.transport = transport
        self.estado_template, self.id_numeric, self.snapshot = estado_template, id_numeric, snapshot
        self.select, self.base_where, self.active = select, base_where, active
        self.nit_exact, self.timeout_s, self.id_len = nit_exact, timeout_s, id_len

    # --- red -----------------------------------------------------------------
    def _get(self, params: dict) -> tuple[list[dict], str]:
        s = get_settings()
        url = s.socrata_url_template.format(dataset=self.dataset)
        host = urlparse(url).hostname
        if host not in s.allowed_connector_hosts:
            raise ConnectorError(f"Host no permitido: {host}")
        try:
            with httpx.Client(timeout=self.timeout_s or s.connector_timeout_s, follow_redirects=False, transport=self.transport) as c:
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
        if not isinstance(data, list) or not all(isinstance(x, dict) for x in data):
            raise ConnectorError("Formato inesperado")
        return data, r.text

    def _params(self, where: str, limit: int) -> dict:
        if self.base_where:
            where = f"({self.base_where}) AND {where}"
        p = {"$where": where, "$limit": str(limit)}
        if self.select:
            p["$select"] = ",".join(self.select)
        if self.snapshot:
            p["$order"] = f"{self.snapshot} DESC"
        return p

    def _estado(self, row: dict) -> str:
        if self.estado_template:
            txt = self.estado_template.format_map(_Blank({k: str(v).strip() for k, v in row.items()}))
            txt = re.sub(r"\(\s*\)", "", txt)                 # columnas vacías: sin paréntesis huérfanos
            return re.sub(r"\s+", " ", txt).strip(" ;")
        return str(row.get(self.fm.get("estado", ""), "")).strip()

    def _to_candidate(self, row: dict) -> Candidate | None:
        oid = str(row.get(self.fm["id"], "")).strip()
        name = str(row.get(self.fm["name"], "")).strip()
        if not oid or not name:
            return None
        extra = {}
        if self.fm.get("nit") and row.get(self.fm["nit"]):
            extra["nit"] = str(row[self.fm["nit"]]).strip()
        if self.snapshot and row.get(self.snapshot):
            extra["corte"] = str(row[self.snapshot]).strip()
        return Candidate(
            source=self.source, official_id=oid, name=name,
            municipio=str(row.get(self.fm.get("municipio", ""), "")).strip(),
            departamento=str(row.get(self.fm.get("departamento", ""), "")).strip(),
            estado_registral=self._estado(row), extra=extra,
        )

    def _valid_id(self, official_id: str) -> bool:
        if not official_id or (self.id_numeric and not official_id.isdigit()):
            return False
        return not self.id_len or self.id_len[0] <= len(official_id) <= self.id_len[1]

    def _latest(self, rows: list[dict]) -> list[dict]:
        """Con columna de corte: conserva solo las filas del corte más reciente."""
        if not self.snapshot or not rows:
            return rows
        def key(r):
            v = str(r.get(self.snapshot, ""))
            return int(v) if v.isdigit() else -1
        top = max(key(r) for r in rows)
        return [r for r in rows if key(r) == top]

    # --- API -----------------------------------------------------------------
    def search(self, query, municipio, official_id, limit=10):
        where, nit = [], None
        oid = (official_id or "").strip()
        if oid:
            d = _digits(oid)
            if self.fm.get("nit") and len(d) >= 9 and self.nit_exact:
                # NIT solo con dígitos en la fuente: igualdad con y sin el dígito de verificación final.
                nit = d[:9]
                where.append(f"{self.fm['nit']} in ('{nit}', '{d}')")
            elif self.fm.get("nit") and len(d) >= 9:
                # NIT con formatos variables en la fuente (puntos, guion, espacios): prefiltro amplio y comparación exacta aquí.
                nit = d[:9]
                where.append(f"{self.fm['nit']} like '%{'%'.join(nit)}%'")
            elif self._valid_id(oid):
                where.append(f"{self.fm['id']}='{_esc(oid)}'")
            else:
                return []
        if query:
            where.append(f"upper({self.fm['name']}) like '{_esc(name_pattern(query))}'")
        if municipio and self.fm.get("municipio"):
            where.append(f"upper({self.fm['municipio']}) like '{_esc(name_pattern(municipio))}'")
        if not where:
            return []
        rows, _ = self._get(self._params(" AND ".join(where), 50 if (self.snapshot or nit) else min(limit, 20)))
        if nit:
            rows = [r for r in rows if _digits(str(r.get(self.fm["nit"], "")))[:9] == nit]
        out, seen = [], set()
        for c in (self._to_candidate(r) for r in rows):          # con corte: filas ordenadas del más reciente
            if c and c.official_id not in seen:
                seen.add(c.official_id)
                out.append(c)
        return out[:limit]

    def get_by_official_id(self, official_id):
        oid = official_id.strip()
        if not self._valid_id(oid):
            return [], {"raw": "", "motivo": "identificador con formato no válido para la fuente"}
        rows, raw = self._get(self._params(f"{self.fm['id']}='{_esc(oid)}'", 50 if self.snapshot else 5))
        rows = self._latest([r for r in rows if str(r.get(self.fm["id"], "")).strip() == oid])
        if self.active and len(rows) > 1:
            col, val = self.active
            act = [r for r in rows if str(r.get(col, "")).strip().upper() == val]
            if len(act) == 1:
                rows = act                          # una sola vigente: es la entidad; las demás son históricas
        cands = [c for c in (self._to_candidate(r) for r in rows) if c]
        return cands, {"raw": raw, "dataset": self.dataset}
