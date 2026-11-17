"""Catálogo de programas académicos (datos abiertos del Ministerio de Educación en datos.gov.co).

- SNIES · `upr9-nkiz` «MEN_PROGRAMAS_DE_EDUCACIÓN_SUPERIOR»: una fila por programa y municipio de oferta.
  AVISO (verificado el 2026-11-16): las columnas `codigoprograma`/`nombreprograma` vienen corridas y contienen
  el código y el nombre del DEPARTAMENTO. El programa se identifica por la combinación exacta
  institución + título obtenido + nivel de formación + municipio (identificador compuesto).
- SIET · `2v94-3ypi` «MEN_PROGRAMAS EDUCACIÓN PARA EL TRABAJO…»: `codigo_programa` único (corte 11/2020).

Igual que las entidades: buscar solo produce candidatos; la verificación consulta por identificador exacto.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
import httpx
from .socrata import SocrataConnector, _esc, name_pattern


@dataclass
class ProgramCandidate:
    source: str
    institution_id: str
    institution_name: str
    program_id: str
    name: str
    level: str = ""
    municipio: str = ""
    estado: str = ""
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# Nivel de formación del dataset SNIES según la modalidad del formato (TC, TL, TE, UN, ES, MG, DOC).
SNIES_LEVELS = {
    "TC": ["Formación técnica profesional"], "TL": ["Tecnológica"], "TE": ["Especialización tecnológica"],
    "UN": ["Universitaria"],
    "ES": ["Especialización universitaria", "Especialización técnico profesional", "Especialización tecnológica", "Especialización médico quirúrgica"],
    "MG": ["Maestría"], "DOC": ["Doctorado"],
}
SEP = " | "
STOP = {"DE", "DEL", "LA", "LAS", "EL", "LOS", "EN", "Y", "E", "O", "U", "A", "AL", "PARA", "POR", "CON", "SU", "SUS"}


def word_patterns(q: str) -> list[str]:
    """Cada palabra significativa como patrón LIKE independiente (cualquier orden): «análisis desarrollo software»
    encuentra «TECNÓLOGO EN ANÁLISIS Y DESARROLLO DE SISTEMAS DE SOFTWARE». Se ignoran conectores y palabras de 1-2 letras."""
    words = [w for w in name_pattern(q).strip("%").split() if len(w) > 2 and w.replace("_", "A") not in STOP]
    return [f"%{w}%" for w in dict.fromkeys(words)][:6]


class ProgramCatalog(SocrataConnector):
    """`cols`: inst, inst_name, title, level, municipio, estado y, si existe, code (código único del programa).
    Sin `code`, el identificador es compuesto: «título | nivel | municipio» dentro de la institución."""

    def __init__(self, source: str, dataset: str, cols: dict, transport: httpx.BaseTransport | None = None,
                 *, active_value: str | None = None, levels: dict | None = None, timeout_s: float | None = None):
        select = tuple(dict.fromkeys(v for v in cols.values() if v))
        super().__init__(source, "program", dataset, {"id": cols["inst"], "name": cols["title"]}, transport=transport,
                         id_numeric=True, select=select, timeout_s=timeout_s)
        self.cols, self.active_value, self.levels = cols, active_value, levels or {}

    # ---------------------------------------------------------------- utilidades
    def _pid(self, row: dict) -> str:
        c = self.cols
        if c.get("code"):
            return str(row.get(c["code"], "")).strip()
        return SEP.join(str(row.get(c[k], "")).strip() for k in ("title", "level", "municipio"))

    def _cand(self, row: dict) -> ProgramCandidate | None:
        c = self.cols
        inst, title = str(row.get(c["inst"], "")).strip(), str(row.get(c["title"], "")).strip()
        if not inst or not title:
            return None
        return ProgramCandidate(source=self.source, institution_id=inst, institution_name=str(row.get(c["inst_name"], "")).strip(),
                                program_id=self._pid(row), name=" ".join(title.split()), level=str(row.get(c["level"], "")).strip(),
                                municipio=str(row.get(c["municipio"], "")).strip(), estado=str(row.get(c["estado"], "")).strip())

    def _params2(self, where: str, limit: int) -> dict:
        p = {"$where": where, "$limit": str(limit), "$select": ",".join(self.select)}
        if self.active_value:
            p["$order"] = f"{self.cols['estado']} ASC"      # «Activo» antes que «Inactivo»
        return p

    def _active(self, rows: list[dict]) -> list[dict]:
        if self.active_value and len(rows) > 1:
            act = [r for r in rows if str(r.get(self.cols["estado"], "")).strip() == self.active_value]
            if len(act) == 1:
                return act
        return rows

    # ---------------------------------------------------------------- API
    def search_programs(self, institution_id: str | None = None, institution_query: str | None = None, municipio: str | None = None,
                        program_query: str | None = None, modalidad: str | None = None, limit: int = 30) -> list[ProgramCandidate]:
        c, where = self.cols, []
        iid = (institution_id or "").strip()
        if iid:
            if not iid.isdigit():
                return []
            where.append(f"{c['inst']}='{_esc(iid)}'")
        elif institution_query and institution_query.strip():
            where.append(f"upper({c['inst_name']}) like '{_esc(name_pattern(institution_query))}'")
        else:
            return []                                   # siempre acotado a una institución
        if program_query and program_query.strip():
            for pat in word_patterns(program_query) or [name_pattern(program_query)]:
                where.append(f"upper({c['title']}) like '{_esc(pat)}'")
        if municipio and municipio.strip():
            where.append(f"upper({c['municipio']}) like '{_esc(name_pattern(municipio))}'")
        lv = self.levels.get(modalidad or "")
        if lv:
            where.append(f"{c['level']} in (" + ", ".join(f"'{_esc(x)}'" for x in lv) + ")")
        rows, _ = self._get(self._params2(" AND ".join(where), 100))
        out, seen = [], set()
        for cand in (self._cand(r) for r in rows):
            if cand and (cand.institution_id, cand.program_id) not in seen:
                seen.add((cand.institution_id, cand.program_id))
                out.append(cand)
        return out[:limit]

    def get_program(self, institution_id: str, program_id: str) -> tuple[list[ProgramCandidate], dict]:
        c = self.cols
        iid, pid = institution_id.strip(), program_id.strip()
        if not iid.isdigit() or not pid:
            return [], {"raw": "", "motivo": "identificador con formato no válido"}
        where = [f"{c['inst']}='{_esc(iid)}'"]
        if c.get("code"):
            if not pid.isdigit():
                return [], {"raw": "", "motivo": "código de programa no válido"}
            where.append(f"{c['code']}='{_esc(pid)}'")
        else:
            parts = pid.split(SEP)
            if len(parts) != 3:
                return [], {"raw": "", "motivo": "identificador compuesto no válido"}
            for k, v in zip(("title", "level", "municipio"), parts):
                where.append(f"{c[k]}='{_esc(v)}'")
        rows, raw = self._get(self._params2(" AND ".join(where), 20))
        rows = [r for r in rows if str(r.get(c["inst"], "")).strip() == iid and self._pid(r) == pid]
        rows = self._active(rows)
        return [x for x in (self._cand(r) for r in rows) if x], {"raw": raw, "dataset": self.dataset}


PROGRAM_DEFS = {
    "snies": ("upr9-nkiz", {"inst": "codigoinstitucion", "inst_name": "nombreinstitucion", "title": "nombretituloobtenido",
                            "level": "nombrenivelformacion", "municipio": "nombremunicipioprograma", "estado": "nombreestadoprograma"},
              {"active_value": "Activo", "levels": SNIES_LEVELS, "timeout_s": 15}),
    "siet": ("2v94-3ypi", {"inst": "codigo_institucion", "inst_name": "nombre_institucion", "title": "nombre_rpograma",
                           "level": "tipo_certificado", "municipio": "municipio", "estado": "estado_programa", "code": "codigo_programa"},
             {"timeout_s": 15}),
}
_overrides: dict[str, ProgramCatalog] = {}


def make_program_catalog(source: str, transport=None) -> ProgramCatalog:
    ds, cols, opts = PROGRAM_DEFS[source]
    return ProgramCatalog(source, ds, cols, transport=transport, **opts)


def set_program_catalog(source: str, cat: ProgramCatalog | None) -> None:
    """Inyección para pruebas."""
    if cat is None:
        _overrides.pop(source, None)
    else:
        _overrides[source] = cat


def get_program_catalog(source: str) -> ProgramCatalog:
    if source in _overrides:
        return _overrides[source]
    if source not in PROGRAM_DEFS:
        raise KeyError(source)
    return make_program_catalog(source)
