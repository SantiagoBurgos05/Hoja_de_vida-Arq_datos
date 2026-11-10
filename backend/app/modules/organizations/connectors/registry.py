from __future__ import annotations
from ....core.config import get_settings
from .base import Connector, ConnectorDisabled
from .socrata import SocrataConnector

# field_map: SUPUESTOS NO VERIFICADOS (ver docs/fuentes.md).
_DEFS = {
    "snies": ("education_higher", "n5yy-8nav", {"id": "codigo_institucion", "name": "nombre_institucion",
              "municipio": "municipio_domicilio", "departamento": "departamento_domicilio", "estado": "estado_institucion"}),
    "siet": ("education_trade", "gpje-sixt", {"id": "codigo_institucion", "name": "nombre_institucion",
             "municipio": "municipio", "departamento": "departamento", "estado": "estado"}),
    "due": ("school", "cfw5-qzt5", {"id": "codigo_dane", "name": "nombre_establecimiento",
            "municipio": "nombre_municipio", "departamento": "nombre_departamento", "estado": "estado"}),
}


class Disabled(Connector):
    enabled = False

    def __init__(self, source: str, kind: str, reason: str):
        self.source, self.kind, self.reason_disabled = source, kind, reason

    def search(self, *a, **k):
        raise ConnectorDisabled(self.reason_disabled)

    def get_by_official_id(self, *a, **k):
        raise ConnectorDisabled(self.reason_disabled)


_overrides: dict[str, Connector] = {}


def set_connector(source: str, c: Connector | None) -> None:
    """Inyección para pruebas."""
    if c is None:
        _overrides.pop(source, None)
    else:
        _overrides[source] = c


def get_connector(source: str) -> Connector:
    if source in _overrides:
        return _overrides[source]
    if source in _DEFS:
        kind, ds, fm = _DEFS[source]
        return SocrataConnector(source, kind, ds, fm)
    s = get_settings()
    if source == "rues":
        # Sin API/dataset oficial verificado. Habilitar solo con canal autorizado y un conector propio.
        return Disabled("rues", "company", "RUES: sin API o dato abierto oficial verificado; requiere canal autorizado.")
    if source == "sigep":
        return Disabled("sigep", "public_entity", "SIGEP: sin API oficial verificada; requiere canal autorizado.")
    raise KeyError(source)
