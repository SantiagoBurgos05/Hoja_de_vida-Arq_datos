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
    # RUES: «Personas Naturales, Personas Jurídicas y ESAL» de Confecámaras (operador del RUES), sincronizado con el RUES.
    # 9,4 M de filas. Se EXCLUYEN las personas naturales (datos personales) y nunca se piden columnas de
    # representantes legales. Identificador: NIT sin dígito de verificación. Sin columna de municipio: se usa la cámara.
    "rues": ("company", "c82u-588k",
             {"id": "nit", "name": "razon_social", "municipio": "camara_comercio", "nit": "nit"},
             {"estado_template": "{estado_matricula}; matrícula {matricula} ({camara_comercio}); último año renovado {ultimo_ano_renovado}",
              "id_numeric": True, "nit_exact": True, "timeout_s": 20, "id_len": (8, 10),   # 99,9 % de los NIT tienen 9 dígitos
              "select": ("nit", "digito_verificacion", "razon_social", "sigla", "organizacion_juridica", "estado_matricula",
                         "camara_comercio", "matricula", "fecha_matricula", "ultimo_ano_renovado", "fecha_cancelacion",
                         "fecha_actualizacion"),
              "base_where": "organizacion_juridica != 'PERSONA NATURAL' AND nit IS NOT NULL",
              "active": ("estado_matricula", "ACTIVA")}),
    # SIGEP: «Universo de entidades» de Función Pública (administra el SIGEP). El código de institución es el código
    # SIGEP (coincide con el directorio de MinTIC kqut-4h4r) y es único; el NIT se repite entre dependencias.
    "sigep": ("public_entity", "h7zv-k39x",
              {"id": "dm_institucion_cod_institucion", "name": "nombre", "municipio": "municipio",
               "departamento": "departamento", "nit": "ccb_nit_inst"},
              {"estado_template": "{estado_ins} en el Universo de entidades (Función Pública); orden {orden}",
               "id_numeric": True, "nit_exact": True,
               "select": ("dm_institucion_cod_institucion", "nombre", "ccb_nit_inst", "orden", "nivel_institucion",
                          "naturaleza_juridica", "sector", "municipio", "departamento", "estado_ins")}),
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
    if source not in _DEFS:
        raise KeyError(source)
    if source in get_settings().disabled_sources:
        # Interruptor operativo (DISABLED_SOURCES): la fuente queda apagada sin cambiar código; se conserva el borrador.
        kind = _DEFS[source][0]
        return Disabled(source, kind, f"{source.upper()}: fuente deshabilitada temporalmente por la administración.")
    return make(source)
