from __future__ import annotations
from ....core.config import get_settings
from .base import Connector, ConnectorDisabled
from .socrata import SocrataConnector

# Columnas CONFIRMADAS contra los datasets reales de datos.gov.co el 2026-11-10 (ver docs/fuentes.md).
# (tipo, dataset, columnas, opciones del conector)
_DEFS = {
    # MEN_INSTITUCIONES EDUCACIÓN SUPERIOR. Una fila por institución (principal o seccional), código único.
    "snies": ("education_higher", "n5yy-8nav",
              {"id": "c_digo_instituci_n", "name": "nombre_instituci_n", "municipio": "municipio_domicilio",
               "departamento": "departamento_domicilio", "nit": "n_mero_identificaci_n"},
              {"estado_template": "{estado} ({fecha_actualizacion})", "id_numeric": True}),
    # MEN_INSTITUCIONES EDUCACIÓN PARA EL TRABAJO Y EL DESARROLLO HUMANO. Sin columna de estado: se informa
    # la licencia de funcionamiento y el corte del dataset (último corte publicado: 11/2020).
    "siet": ("education_trade", "gpje-sixt",
             {"id": "codigo_institucion", "name": "nombre_institucion", "municipio": "municipio",
              "departamento": "departamento", "nit": "nit"},
             {"estado_template": "Licencia de funcionamiento {licencia}; corte {mes_corte}/{a_o_corte}", "id_numeric": True}),
    # MEN_ESTABLECIMIENTOS_EDUCATIVOS_PREESCOLAR_BÁSICA_Y_MEDIA. Repite cada establecimiento por año (a_o):
    # se usa el año más reciente en que aparece el código DANE. Aproximación a DUE / Buscando Colegio.
    "due": ("school", "cfw5-qzt5",
            {"id": "codigo_dane", "name": "nombre_establecimiento", "municipio": "municipio", "departamento": "departamento"},
            {"estado_template": "Reportado en el directorio del MEN, año {a_o}", "id_numeric": True, "snapshot": "a_o"}),
}


def make(source: str, transport=None) -> SocrataConnector:
    """Construye el conector oficial de una fuente (las pruebas inyectan `transport`)."""
    kind, ds, fm, opts = _DEFS[source]
    return SocrataConnector(source, kind, ds, fm, transport=transport, **opts)


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
        return make(source)
    s = get_settings()
    if source == "rues":
        # Sin API/dataset oficial verificado. Habilitar solo con canal autorizado y un conector propio.
        return Disabled("rues", "company", "RUES: sin API o dato abierto oficial verificado; requiere canal autorizado.")
    if source == "sigep":
        return Disabled("sigep", "public_entity", "SIGEP: sin API oficial verificada; requiere canal autorizado.")
    raise KeyError(source)
