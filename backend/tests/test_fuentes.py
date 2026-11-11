"""Paso 3: conectores con las columnas reales de datos.gov.co (filas sintéticas, estructura real)."""
import pytest
from urllib.parse import parse_qs, unquote, urlparse
from app.modules.organizations.connectors import registry
from app.modules.organizations.connectors.socrata import name_pattern
from .helpers import edu_payload, mock_source, reset_connectors, snies_row


@pytest.fixture(autouse=True)
def _clean():
    reset_connectors()
    yield
    reset_connectors()


def _where(url):
    return unquote(parse_qs(urlparse(url).query)["$where"][0])


def due_row(code, name, year, municipio="Bogotá, D.C."):
    return {"a_o": str(year), "codigo_dane": code, "nombre_establecimiento": name, "municipio": municipio, "departamento": "Bogotá, D.C."}


def siet_row(code, name, nit="830000000-1"):
    return {"codigo_institucion": code, "nombre_institucion": name, "nit": nit, "licencia": "160037", "municipio": "BOGOTÁ",
            "departamento": "BOGOTÁ D.C.", "mes_corte": "11", "a_o_corte": "2020"}


def _verify(client, u, source, oid, rt, rid):
    return client.post("/api/organizations/verify", json={"source": source, "official_id": oid, "record_type": rt, "record_id": rid},
                       headers=u["headers"]).json()


def test_columnas_confirmadas_por_fuente():
    assert registry.make("snies").fm["id"] == "c_digo_instituci_n"
    assert registry.make("siet").fm["id"] == "codigo_institucion"
    d = registry.make("due")
    assert d.fm["id"] == "codigo_dane" and d.snapshot == "a_o"


def test_patron_de_nombre_tolera_tildes_y_neutraliza_comodines():
    assert name_pattern("Politécnico") == "%P_L_T_CN_C_%"
    assert name_pattern("  minuto   de dios ") == "%M_N_T_ D_ D__S%"
    assert "%" not in name_pattern("a%b")[1:-1]


def test_busqueda_usa_columnas_reales_y_escapa(client, alice):
    calls = []
    mock_source("snies", [], calls=calls)
    client.post("/api/organizations/search", json={"source": "snies", "query": "Politécnico' OR '1'='1", "municipio": "Bogotá"},
                headers=alice["headers"])
    w = _where(calls[0])
    assert "upper(nombre_instituci_n) like '%P_L_T_CN_C_'' _R ''1''=''1%'" in w
    assert "upper(municipio_domicilio) like '%B_G_T_%'" in w


def test_busqueda_por_nit_compara_digitos(client, alice):
    calls = []
    rows = [snies_row("2829", "CORPORACION SINTETICA", "Bogotá, D.C.", "Bogotá, D.C.", nit="800.116.217-2"),
            snies_row("9999", "OTRA", "Cali", "Valle", nit="800.116.200-1")]
    mock_source("snies", rows, calls=calls)
    r = client.post("/api/organizations/search", json={"source": "snies", "official_id": "800116217-2"}, headers=alice["headers"]).json()
    assert [c["official_id"] for c in r["candidates"]] == ["2829"] and r["candidates"][0]["extra"]["nit"] == "800.116.217-2"
    assert "n_mero_identificaci_n like" in _where(calls[0])


def test_identificador_no_numerico_no_consulta_ni_verifica(client, alice):
    calls = []
    mock_source("snies", [snies_row("1101", "X", "B", "B")], calls=calls)
    e = client.post("/api/education", json=edu_payload(), headers=alice["headers"]).json()
    r = _verify(client, alice, "snies", "11a01", "education_higher", e["id"])
    assert r["organization_status"] == "not_found" and calls == []


def test_siet_informa_licencia_y_corte(client, alice):
    mock_source("siet", [siet_row("1112", "CENTRO SINTETICO DE FORMACION")])
    e = client.post("/api/education", json=edu_payload(modalidad="TL"), headers=alice["headers"]).json()
    r = _verify(client, alice, "siet", "1112", "education_higher", e["id"])
    assert r["organization_status"] == "verified"
    assert r["organization"]["estado_registral"] == "Licencia de funcionamiento 160037; corte 11/2020"


def test_due_usa_el_anio_mas_reciente_del_codigo(client, alice):
    mock_source("due", [due_row("311001000001", "COLEGIO SINTETICO MAYOR", 2025), due_row("311001000001", "COL SINTETICO MAYOR", 2024)])
    resume = client.get("/api/resume", headers=alice["headers"]).json()
    r = _verify(client, alice, "due", "311001000001", "education_basic", resume["id"])
    assert r["organization_status"] == "verified"                      # varios años del mismo código NO son ambigüedad
    assert r["organization"]["name"] == "COLEGIO SINTETICO MAYOR" and "2025" in r["organization"]["estado_registral"]


def test_due_codigo_repetido_en_el_mismo_anio_es_ambiguo(client, alice):
    mock_source("due", [due_row("376275001461", "COLEGIO A", 2025), due_row("376275001461", "COLEGIO B", 2025)])
    resume = client.get("/api/resume", headers=alice["headers"]).json()
    r = _verify(client, alice, "due", "376275001461", "education_basic", resume["id"])
    assert r["organization_status"] == "pending" and r["organization"] is None


def test_due_busqueda_sin_repetir_por_anio(client, alice):
    calls = []
    rows = [due_row("1", "COLEGIO SINTETICO", 2025), due_row("1", "COLEGIO SINTETICO", 2024), due_row("2", "COLEGIO SINTETICO II", 2023)]
    mock_source("due", rows, calls=calls)
    r = client.post("/api/organizations/search", json={"source": "due", "query": "colegio sintetico"}, headers=alice["headers"]).json()
    assert [c["official_id"] for c in r["candidates"]] == ["1", "2"]
    assert parse_qs(urlparse(calls[0]).query)["$order"] == ["a_o DESC"]


def test_respuesta_malformada_no_concede(client, alice):
    mock_source("snies", body="[1, 2]")
    r = client.post("/api/organizations/search", json={"source": "snies", "query": "x"}, headers=alice["headers"]).json()
    assert r["organization_status"] == "error" and r["candidates"] == []


def test_fallo_al_guardar_evidencia_no_concede_verificacion(client, alice):
    """Si Storage rechaza la evidencia (p. ej. bucket que no admite JSON), no hay verificación ni error 500."""
    from app.core import storage as st
    mock_source("snies", [snies_row("1101", "UNIVERSIDAD SINTETICA", "B", "B")])
    e = client.post("/api/education", json=edu_payload(), headers=alice["headers"]).json()
    real = st.get_storage()

    class RechazaJson:
        def put(self, key, data, ctype):
            if ctype == "application/json":
                raise st.StorageError("Supabase put HTTP 400")
            return real.put(key, data, ctype)

        def get(self, *a): return real.get(*a)
        def size(self, *a): return real.size(*a)
        def delete(self, *a): return real.delete(*a)
    st.set_storage(RechazaJson())
    try:
        r = client.post("/api/organizations/verify", json={"source": "snies", "official_id": "1101", "record_type": "education_higher",
                                                           "record_id": e["id"]}, headers=alice["headers"])
    finally:
        st.set_storage(real)
    assert r.status_code == 200 and r.json()["organization_status"] == "error" and r.json()["organization"] is None
    assert client.get("/api/education", headers=alice["headers"]).json()[0]["organization_status"] == "error"



# ------------------------------------------------------------------ RUES / SIGEP
def rues_row(nit, name, estado="ACTIVA", camara="BOGOTA", matricula="100"):
    return {"nit": nit, "digito_verificacion": "1", "razon_social": name, "organizacion_juridica": "SOCIEDADES POR ACCIONES SIMPLIFICADAS SAS",
            "estado_matricula": estado, "camara_comercio": camara, "matricula": matricula, "ultimo_ano_renovado": "2026"}


def sigep_row(code, name, nit="899999001"):
    return {"dm_institucion_cod_institucion": code, "nombre": name, "ccb_nit_inst": nit, "orden": "NACIONAL",
            "municipio": "BOGOTÁ. D.C.", "departamento": "BOGOTÁ. D.C.", "estado_ins": "ACTIVA"}


def _work(client, u, tipo):
    from .helpers import work_payload
    cat = "empleado_privado" if tipo == "privada" else "servidor_publico"
    return client.post("/api/work", json=work_payload(tipo_entidad=tipo, categoria_tiempo=cat), headers=u["headers"]).json()


def test_rues_consulta_sin_personas_naturales_ni_datos_de_representantes(client, alice):
    calls = []
    mock_source("rues", [rues_row("900000001", "EMPRESA SINTETICA SAS")], calls=calls)
    client.post("/api/organizations/search", json={"source": "rues", "query": "empresa sintetica"}, headers=alice["headers"])
    q = parse_qs(urlparse(calls[0]).query)
    assert "organizacion_juridica != 'PERSONA NATURAL'" in q["$where"][0] and "nit IS NOT NULL" in q["$where"][0]
    cols = q["$select"][0].split(",")
    assert "razon_social" in cols and not [c for c in cols if "representante" in c or "nombre" in c or "apellido" in c]


def test_rues_verifica_empresa_por_nit_y_habilita_soportes(client, alice):
    from .test_documents import up
    mock_source("rues", [rues_row("900000001", "EMPRESA SINTETICA SAS")])
    w = _work(client, alice, "privada")
    r = _verify(client, alice, "rues", "900000001", "work", w["id"])
    assert r["organization_status"] == "verified" and r["organization"]["name"] == "EMPRESA SINTETICA SAS"
    assert r["organization"]["estado_registral"].startswith("ACTIVA; matrícula 100 (BOGOTA)")
    assert up(client, alice, w["id"], rt="work").status_code == 201          # certificado laboral habilitado


def test_rues_busqueda_por_nit_con_digito_de_verificacion(client, alice):
    calls = []
    mock_source("rues", [rues_row("900000001", "EMPRESA SINTETICA SAS")], calls=calls)
    r = client.post("/api/organizations/search", json={"source": "rues", "official_id": "900.000.001-7"}, headers=alice["headers"]).json()
    assert [c["official_id"] for c in r["candidates"]] == ["900000001"]
    assert "nit in ('9000000017', '900000001')" in _where(calls[0])


def test_rues_busqueda_nit_de_8_digitos_con_dv(client, alice):
    mock_source("rues", [rues_row("80014238", "EMPRESA SINTETICA OCHO")])
    r = client.post("/api/organizations/search", json={"source": "rues", "official_id": "80.014.238-5"}, headers=alice["headers"]).json()
    assert [c["official_id"] for c in r["candidates"]] == ["80014238"]


def test_rues_prefiere_la_unica_matricula_activa(client, alice):
    rows = [rues_row("900000002", "EMPRESA SINTETICA DOS SAS", "MATRÍCULA CANCELADA POR TRASLADO DE DOMICILIO", "CALI", "1"),
            rues_row("900000002", "EMPRESA SINTETICA DOS SAS", "ACTIVA", "BOGOTA", "2")]
    mock_source("rues", rows)
    w = _work(client, alice, "privada")
    r = _verify(client, alice, "rues", "900000002", "work", w["id"])
    assert r["organization_status"] == "verified" and "matrícula 2 (BOGOTA)" in r["organization"]["estado_registral"]


def test_rues_nit_con_varias_matriculas_activas_es_ambiguo(client, alice):
    mock_source("rues", [rues_row("999999999", "A"), rues_row("999999999", "B", matricula="2")])
    w = _work(client, alice, "privada")
    r = _verify(client, alice, "rues", "999999999", "work", w["id"])
    assert r["organization_status"] == "pending" and r["organization"] is None


def test_rues_empresa_cancelada_se_verifica_con_su_estado(client, alice):
    """Una empresa cancelada existió: se verifica, y el estado registral lo dice (no se presenta como vigente)."""
    mock_source("rues", [rues_row("900000003", "EMPRESA LIQUIDADA SAS", "CANCELADA")])
    w = _work(client, alice, "privada")
    r = _verify(client, alice, "rues", "900000003", "work", w["id"])
    assert r["organization_status"] == "verified" and r["organization"]["estado_registral"].startswith("CANCELADA")


def test_sigep_verifica_entidad_publica_por_codigo(client, alice):
    calls = []
    mock_source("sigep", [sigep_row("0011", "MINISTERIO DE EDUCACION NACIONAL")], calls=calls)
    w = _work(client, alice, "publica")
    r = _verify(client, alice, "sigep", "0011", "work", w["id"])
    assert r["organization_status"] == "verified" and r["organization"]["official_id"] == "0011"
    assert "ACTIVA en el Universo de entidades" in r["organization"]["estado_registral"]
    cols = parse_qs(urlparse(calls[0]).query)["$select"][0].split(",")
    assert "email" not in cols and "nombre_representante" not in cols


def test_sigep_nit_compartido_lista_candidatos_sin_verificar(client, alice):
    mock_source("sigep", [sigep_row("1479", "CONCEJO SINTETICO", "899999061"), sigep_row("6126", "SECRETARIA SINTETICA", "899999061")])
    r = client.post("/api/organizations/search", json={"source": "sigep", "official_id": "899999061"}, headers=alice["headers"]).json()
    assert {c["official_id"] for c in r["candidates"]} == {"1479", "6126"} and r["organization_status"] == "pending"



def test_rues_nit_de_relleno_no_se_consulta(client, alice):
    calls = []
    mock_source("rues", [rues_row("1", "ASOCIACION CON NIT DE RELLENO")], calls=calls)
    w = _work(client, alice, "privada")
    r = _verify(client, alice, "rues", "1", "work", w["id"])
    assert r["organization_status"] == "not_found" and calls == []
