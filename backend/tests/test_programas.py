"""Verificación de programas académicos (SNIES `upr9-nkiz`, SIET `2v94-3ypi`). Filas sintéticas con columnas reales."""
from urllib.parse import parse_qs, unquote, urlparse
import httpx
import pytest
from app.core.db import get_db
from app.modules.organizations.connectors import programs as P
from .helpers import SNIES_ROWS, edu_payload, mock_source, reset_connectors, verified_education


def snies_prog(title, level="Universitaria", mun="BOGOTA", estado="Activo", inst="1101", inst_name="UNIVERSIDAD SINTETICA DEL NORTE"):
    return {"codigoinstitucion": inst, "nombreinstitucion": inst_name, "nombretituloobtenido": title, "nombrenivelformacion": level,
            "nombremunicipioprograma": mun, "nombreestadoprograma": estado,
            "codigoprograma": "11", "nombreprograma": "Bogotá D.C."}     # columnas corridas en la fuente real: no se usan


def siet_prog(code, name, inst="1112"):
    return {"codigo_institucion": inst, "nombre_institucion": "CENTRO SINTETICO", "codigo_programa": code, "nombre_rpograma": name,
            "tipo_certificado": "TÉCNICO LABORAL", "municipio": "BOGOTÁ", "estado_programa": "REGISTRO RENOVADO"}


def mock_programs(source, rows=None, calls=None, boom=None):
    def handler(req: httpx.Request):
        if calls is not None:
            calls.append(str(req.url))
        if boom:
            raise boom
        return httpx.Response(200, json=rows or [])
    P.set_program_catalog(source, P.make_program_catalog(source, transport=httpx.MockTransport(handler)))


@pytest.fixture(autouse=True)
def _clean():
    reset_connectors(); P.set_program_catalog("snies", None); P.set_program_catalog("siet", None)
    yield
    reset_connectors(); P.set_program_catalog("snies", None); P.set_program_catalog("siet", None)


def _where(url):
    return unquote(parse_qs(urlparse(url).query)["$where"][0])


def _search(client, u, **body):
    return client.post("/api/organizations/programs/search", json=body, headers=u["headers"]).json()


def _verify(client, u, source, inst, pid, rid):
    return client.post("/api/organizations/programs/verify", json={"source": source, "institution_id": inst, "program_id": pid, "record_id": rid},
                       headers=u["headers"]).json()


def _rec(client, u):
    return client.get("/api/education", headers=u["headers"]).json()[0]


# ----------------------------------------------------------------- búsqueda
def test_palabras_en_cualquier_orden_y_nivel_segun_modalidad(client, alice):
    calls = []
    mock_programs("snies", [snies_prog("TECNOLOGO EN ANALISIS Y DESARROLLO DE SISTEMAS DE SOFTWARE", "Tecnológica")], calls)
    r = _search(client, alice, source="snies", institution_query="sena", program_query="análisis y desarrollo de software", modalidad="TL")
    assert r["program_status"] == "pending" and len(r["candidates"]) == 1
    w = _where(calls[0])
    assert "upper(nombreinstitucion) like '%S_N_%'" in w
    for pat in ("%_N_L_S%", "%D_S_RR%", "%S_FTW_%"):
        assert f"upper(nombretituloobtenido) like '{pat}'" in w          # cada palabra por separado, recortada a su raíz
    assert "nombrenivelformacion in ('Tecnológica')" in w
    assert " DE%" not in w and "'%Y%'" not in w                           # conectores ignorados


def test_programas_de_una_institucion_por_codigo(client, alice):
    calls = []
    mock_programs("snies", [snies_prog("INGENIERO DE SISTEMAS"), snies_prog("ADMINISTRADOR DE EMPRESAS")], calls)
    r = _search(client, alice, source="snies", institution_id="1101")
    assert [c["name"] for c in r["candidates"]] == ["INGENIERO DE SISTEMAS", "ADMINISTRADOR DE EMPRESAS"]
    assert "codigoinstitucion='1101'" in _where(calls[0])
    sel = parse_qs(urlparse(calls[0]).query)["$select"][0].split(",")
    assert "codigoprograma" not in sel and "nombreprograma" not in sel     # columnas corridas: no se piden


def test_raiz_de_palabras_tolera_variaciones_del_titulo():
    import re
    def hit(q, title):
        rx = [re.compile("^" + p.replace("%", ".*").replace("_", ".") + "$") for p in P.word_patterns(q)]
        return all(r.match(title) for r in rx)
    assert hit("Tecnología en análisis y desarrollo de software", "TECNOLOGO EN ANALISIS Y DESARROLLO DE SISTEMAS DE SOFTWARE")
    assert hit("Licenciatura en educación infantil", "LICENCIADO EN EDUCACION INFANTIL")
    assert hit("Administración de empresas", "ADMINISTRADOR DE EMPRESAS")


def test_busqueda_por_nit_resuelve_los_codigos_de_la_institucion(client, alice):
    """El catálogo de programas no tiene NIT: el NIT se convierte en los códigos de las sedes que lo comparten."""
    mock_source("snies", SNIES_ROWS)                            # las 3 sedes comparten el NIT 900.000.000-1
    calls = []
    mock_programs("snies", [snies_prog("TECNOLOGO EN SISTEMAS", "Tecnológica")], calls)
    r = _search(client, alice, source="snies", institution_id="900000000-1", program_query="sistemas", modalidad="TL")
    assert len(r["candidates"]) == 1
    w = _where(calls[0])
    assert "codigoinstitucion in ('1101', '11010', '2202')" in w and "900000000" not in w


def test_nit_inexistente_lo_indica(client, alice):
    mock_source("snies", [])
    calls = []
    mock_programs("snies", [], calls)
    r = _search(client, alice, source="snies", institution_id="123456789", program_query="sistemas")
    assert r["candidates"] == [] and "NIT" in r["message"] and calls == []


def test_sin_coincidencias_relaja_nivel_y_luego_palabras(client, alice):
    """Modalidad declarada distinta al nivel oficial: se muestran los programas de otros niveles; palabras sin
    coincidencia: se listan los programas de la institución. El mensaje explica qué filtro se relajó."""
    calls = []
    def handler(req):
        calls.append(str(req.url)); w = _where(str(req.url))
        if "nombrenivelformacion in" in w:
            return httpx.Response(200, json=[])                 # nada de nivel Universitaria
        return httpx.Response(200, json=[snies_prog("TECNOLOGO EN SISTEMAS", "Tecnológica")])
    P.set_program_catalog("snies", P.make_program_catalog("snies", transport=httpx.MockTransport(handler)))
    r = _search(client, alice, source="snies", institution_id="1101", program_query="sistemas", modalidad="UN", municipio="bogota")
    assert len(r["candidates"]) == 1 and "otros niveles" in r["message"]
    w2 = _where(calls[1])
    assert "nombrenivelformacion" not in w2 and "nombremunicipioprograma" not in w2 and "nombretituloobtenido" in w2

    calls.clear()
    def handler2(req):
        calls.append(str(req.url))
        return httpx.Response(200, json=[] if "nombretituloobtenido" in _where(str(req.url)) else [snies_prog("ADMINISTRADOR DE EMPRESAS")])
    P.set_program_catalog("snies", P.make_program_catalog("snies", transport=httpx.MockTransport(handler2)))
    r = _search(client, alice, source="snies", institution_id="1101", program_query="xyz palabras", modalidad="UN")
    assert [c["name"] for c in r["candidates"]] == ["ADMINISTRADOR DE EMPRESAS"] and "No encontramos" in r["message"]
    assert all("codigoinstitucion='1101'" in _where(u) for u in calls)       # siempre acotado a la institución


def test_busqueda_exige_institucion(client, alice):
    r = client.post("/api/organizations/programs/search", json={"source": "snies", "program_query": "sistemas"}, headers=alice["headers"])
    assert r.status_code == 422


# -------------------------------------------------------------- verificación
def test_verificar_programa_snies_por_identificador_compuesto(client, alice):
    rid = verified_education(client, alice, program=False)
    rows = [snies_prog("INGENIERO  DE SISTEMAS", mun="BOGOTA")]
    calls = []
    mock_programs("snies", rows, calls)
    cand = _search(client, alice, source="snies", institution_id="1101", program_query="sistemas")["candidates"][0]
    assert cand["program_id"] == "INGENIERO  DE SISTEMAS | Universitaria | BOGOTA" and cand["name"] == "INGENIERO DE SISTEMAS"
    r = _verify(client, alice, "snies", "1101", cand["program_id"], rid)
    assert r["program_status"] == "verified" and r["program"]["name"] == "INGENIERO DE SISTEMAS" and "NO acredita" in r["message"]
    w = _where(calls[-1])
    assert "nombretituloobtenido='INGENIERO  DE SISTEMAS'" in w and "nombrenivelformacion='Universitaria'" in w and "nombremunicipioprograma='BOGOTA'" in w
    rec = _rec(client, alice)
    assert rec["program_status"] == "verified" and rec["program"]["level"] == "Universitaria"
    from bson import ObjectId
    ev = get_db().lake_objects.find_one({"_id": ObjectId(r["program"]["evidence_id"])})
    assert ev["kind"] == "program_evidence" and ev["layer"] == "bronze"
    silver = get_db().silver_records.find_one({"source_id": rid})
    assert silver["data"]["program_status"] == "verified" and silver["data"]["programa_oficial"] == "INGENIERO DE SISTEMAS"


def test_busqueda_combinada_verifica_institucion_y_programa(client, alice):
    """«sena» + «análisis desarrollo software»: al elegir el programa se verifican la institución y el programa."""
    mock_source("snies", SNIES_ROWS)
    mock_programs("snies", [snies_prog("TECNOLOGO EN ANALISIS Y DESARROLLO DE SOFTWARE", "Tecnológica")])
    e = client.post("/api/education", json=edu_payload(modalidad="TL"), headers=alice["headers"]).json()
    assert e["program_status"] == "pending" and e["organization_status"] == "pending"
    r = _verify(client, alice, "snies", "1101", "TECNOLOGO EN ANALISIS Y DESARROLLO DE SOFTWARE | Tecnológica | BOGOTA", e["id"])
    assert r["program_status"] == "verified" and r["organization_status"] == "verified"
    rec = _rec(client, alice)
    assert rec["organization_status"] == "verified" and rec["program_status"] == "verified"


def test_institucion_no_verificada_no_verifica_programa(client, alice):
    mock_source("snies", [])                                   # la institución no existe
    mock_programs("snies", [snies_prog("INGENIERO DE SISTEMAS", inst="999")])
    e = client.post("/api/education", json=edu_payload(), headers=alice["headers"]).json()
    r = _verify(client, alice, "snies", "999", "INGENIERO DE SISTEMAS | Universitaria | BOGOTA", e["id"])
    assert r["program_status"] == "pending" and r["organization_status"] == "not_found" and r["program"] is None
    assert _rec(client, alice)["program_status"] == "pending"


def test_programa_inexistente_y_ambiguo(client, alice):
    rid = verified_education(client, alice, program=False)
    mock_programs("snies", [])
    assert _verify(client, alice, "snies", "1101", "OTRO | Universitaria | BOGOTA", rid)["program_status"] == "not_found"
    mock_programs("snies", [snies_prog("INGENIERO DE SISTEMAS"), snies_prog("INGENIERO DE SISTEMAS")])
    assert _verify(client, alice, "snies", "1101", "INGENIERO DE SISTEMAS | Universitaria | BOGOTA", rid)["program_status"] == "pending"


def test_prefiere_el_unico_registro_activo(client, alice):
    rid = verified_education(client, alice, program=False)
    mock_programs("snies", [snies_prog("INGENIERO DE SISTEMAS", estado="Activo"), snies_prog("INGENIERO DE SISTEMAS", estado="Inactivo")])
    r = _verify(client, alice, "snies", "1101", "INGENIERO DE SISTEMAS | Universitaria | BOGOTA", rid)
    assert r["program_status"] == "verified" and r["program"]["estado"] == "Activo"


def test_identificador_compuesto_malformado(client, alice):
    rid = verified_education(client, alice, program=False)
    calls = []
    mock_programs("snies", [snies_prog("X")], calls)
    assert _verify(client, alice, "snies", "1101", "solo-un-campo", rid)["program_status"] == "not_found" and calls == []


def test_siet_verifica_por_codigo_de_programa(client, alice):
    mock_source("siet", [{"codigo_institucion": "1112", "nombre_institucion": "CENTRO SINTETICO", "nit": "830000000-1", "licencia": "1",
                          "municipio": "BOGOTÁ", "departamento": "BOGOTÁ D.C.", "mes_corte": "11", "a_o_corte": "2020"}])
    calls = []
    mock_programs("siet", [siet_prog("41952", "TÉCNICO LABORAL EN SISTEMAS INFORMATICOS")], calls)
    e = client.post("/api/education", json=edu_payload(modalidad="TC"), headers=alice["headers"]).json()
    r = _verify(client, alice, "siet", "1112", "41952", e["id"])
    assert r["program_status"] == "verified" and r["program"]["program_id"] == "41952"
    assert "codigo_programa='41952'" in _where(calls[-1])


def test_falla_de_la_fuente_conserva_y_no_revoca(client, alice):
    rid = verified_education(client, alice, program=False)
    mock_programs("snies", [snies_prog("INGENIERO DE SISTEMAS")])
    assert _verify(client, alice, "snies", "1101", "INGENIERO DE SISTEMAS | Universitaria | BOGOTA", rid)["program_status"] == "verified"
    mock_programs("snies", boom=httpx.ConnectTimeout("lento"))
    assert _verify(client, alice, "snies", "1101", "INGENIERO DE SISTEMAS | Universitaria | BOGOTA", rid)["program_status"] == "error"
    assert _rec(client, alice)["program_status"] == "verified"           # una falla no revoca


# -------------------------------------------------------------- coherencia
def test_cambiar_modalidad_invalida_el_programa(client, alice):
    rid = verified_education(client, alice, program=False)
    mock_programs("snies", [snies_prog("INGENIERO DE SISTEMAS")])
    _verify(client, alice, "snies", "1101", "INGENIERO DE SISTEMAS | Universitaria | BOGOTA", rid)
    rec = _rec(client, alice)
    r = client.put(f"/api/education/{rid}", json=edu_payload(modalidad="MG", revision=rec["revision"]), headers=alice["headers"]).json()
    assert r["program_status"] == "pending" and r["program"] is None
    assert r["organization_status"] == "verified"                        # la institución sigue verificada


def test_otros_cambios_conservan_el_programa(client, alice):
    rid = verified_education(client, alice, program=False)
    mock_programs("snies", [snies_prog("INGENIERO DE SISTEMAS")])
    _verify(client, alice, "snies", "1101", "INGENIERO DE SISTEMAS | Universitaria | BOGOTA", rid)
    rec = _rec(client, alice)
    r = client.put(f"/api/education/{rid}", json=edu_payload(semestres_aprobados=8, revision=rec["revision"]), headers=alice["headers"]).json()
    assert r["program_status"] == "verified"


def test_cambiar_de_institucion_reinicia_el_programa(client, alice):
    rid = verified_education(client, alice, program=False)
    mock_programs("snies", [snies_prog("INGENIERO DE SISTEMAS")])
    _verify(client, alice, "snies", "1101", "INGENIERO DE SISTEMAS | Universitaria | BOGOTA", rid)
    client.post("/api/organizations/verify", json={"source": "snies", "official_id": "2202", "record_type": "education_higher", "record_id": rid},
                headers=alice["headers"])
    rec = _rec(client, alice)
    assert rec["organization_status"] == "verified" and rec["program_status"] == "pending" and rec["program"] is None


def test_cliente_no_puede_declarar_programa_verificado(client, alice):
    e = client.post("/api/education", json=edu_payload(), headers=alice["headers"]).json()
    r = client.put(f"/api/education/{e['id']}", json={**edu_payload(revision=e["revision"]), "program_status": "verified"}, headers=alice["headers"])
    assert r.status_code == 422


def test_registro_ajeno_404(client, alice, bob):
    rid = verified_education(client, alice, program=False)
    mock_programs("snies", [snies_prog("INGENIERO DE SISTEMAS")])
    r = client.post("/api/organizations/programs/verify", json={"source": "snies", "institution_id": "1101",
                    "program_id": "INGENIERO DE SISTEMAS | Universitaria | BOGOTA", "record_id": rid}, headers=bob["headers"])
    assert r.status_code == 404
