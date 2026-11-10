from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional


class ConnectorDisabled(Exception):
    """La fuente está deshabilitada (sin vía oficial autorizada)."""


class ConnectorError(Exception):
    """Fallo de red, timeout, respuesta no válida o host no permitido."""


@dataclass
class Candidate:
    source: str
    official_id: str
    name: str
    municipio: str = ""
    departamento: str = ""
    estado_registral: str = ""     # estado que reporta la fuente (p. ej. «Activa»); vacío si no lo informa
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class Connector:
    source: str = ""
    kind: str = ""        # education_higher | education_trade | school | company | public_entity
    enabled: bool = True
    reason_disabled: str = ""

    def search(self, query: str | None, municipio: str | None, official_id: str | None, limit: int = 10) -> list[Candidate]:
        raise NotImplementedError

    def get_by_official_id(self, official_id: str) -> tuple[list[Candidate], dict]:
        """Devuelve (coincidencias exactas por identificador, respuesta cruda para evidencia)."""
        raise NotImplementedError
