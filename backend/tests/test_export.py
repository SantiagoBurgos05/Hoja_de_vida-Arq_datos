"""Exportación: formato (3 páginas, plantilla intacta), contenido y espacios que NO deben completarse."""
import io
import pytest
import pdfplumber
from pypdf import PdfReader
from app.modules.export import layout as L, service as exp
from .helpers import edu_payload, reset_connectors, verified_education, work_payload
from .test_resume import save

TEMPLATE_WORDS = None


def words(pdf_bytes, page):
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as p:
        return p.pages[page].extract_words(), p.pages[page]


def added_chars(pdf_bytes, page):
    """Caracteres presentes en el PDF exportado y ausentes de la plantilla (pdfplumber fusiona palabras solapadas; los caracteres no)."""
    with pdfplumber.open(io.BytesIO(template_bytes())) as t, pdfplumber.open(io.BytesIO(pdf_bytes)) as o:
        tch = {(round(c["x0"], 1), round(c["top"], 1), c["text"]) for c in t.pages[page].chars}
        return [c for c in o.pages[page].chars if (round(c["x0"], 1), round(c["top"], 1), c["text"]) not in tch]


def template_bytes():
    return exp.TEMPLATE.read_bytes()


def fill(client, u, n_work=1, n_edu=1):
    client.get("/api/resume", headers=u["headers"]); save(client, u, 0)
    for i in range(n_edu):
        client.post("/api/education", json=edu_payload(nombre_estudios=f"Programa {i}", terminacion={"mes": 6, "anio": 2000 + i}), headers=u["headers"])
    for i in range(n_work):
        client.post("/api/work", json=work_payload(cargo=f"Cargo {i}", fecha_ingreso=f"20{10+i:02d}-01-01", fecha_retiro=f"20{10+i:02d}-12-31"), headers=u["headers"])


def get_pdf(client, u):
    r = client.get("/api/export/pdf", headers=u["headers"])
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    return r.content


def test_tres_paginas_y_plantilla_intacta(client, alice):
    fill(client, alice)
    pdf = get_pdf(client, alice)
    assert len(PdfReader(io.BytesIO(pdf)).pages) == 3
    assert [p.mediabox.width for p in PdfReader(io.BytesIO(pdf)).pages] == [612, 612, 612]
    # todos los rótulos de la plantilla siguen presentes y en su sitio
    for pg in range(3):
        with pdfplumber.open(io.BytesIO(template_bytes())) as t, pdfplumber.open(io.BytesIO(pdf)) as o:
            tch = {(round(c["x0"], 1), round(c["top"], 1), c["text"]) for c in t.pages[pg].chars}
            och = {(round(c["x0"], 1), round(c["top"], 1), c["text"]) for c in o.pages[pg].chars}
            assert not (tch - och), f"p{pg+1}: {sorted(tch - och)[:5]}"
            assert (len(o.pages[pg].lines), len(o.pages[pg].rects), len(o.pages[pg].curves)) == (len(t.pages[pg].lines), len(t.pages[pg].rects), len(t.pages[pg].curves))


def test_contenido_en_las_casillas_correctas(client, alice):
    fill(client, alice)
    pdf = get_pdf(client, alice)
    w1, _ = words(pdf, 0)
    tw1, _ = words(template_bytes(), 0)
    tset = {(round(w["x0"]), round(w["top"]), w["text"]) for w in tw1}
    added = [w for w in w1 if (round(w["x0"]), round(w["top"]), w["text"]) not in tset]
    def at(text):
        return [w for w in added if w["text"] == text]
    # apellidos y nombres en su caja de la fila 1 (y entre 160 y 195)
    assert at("PRUEBA")[0]["top"] < 190 and at("PRUEBA")[0]["x0"] < 100
    assert at("SINTETICA") and 220 < at("SINTETICA")[0]["x0"] < 260
    assert at("ANA") and at("ANA")[0]["x0"] > 390
    # número de documento sobre la línea "No."
    d = at("1000000000")[0]
    assert 180 < d["x0"] < 200 and 205 < d["top"] < 222
    # fecha de nacimiento en las casillas DÍA/MES/AÑO
    assert any(135 < w["x0"] < 150 and 276 < w["top"] < 290 for w in at("20")), [(w["text"], w["x0"], w["top"]) for w in added if w["top"] > 270 and w["top"] < 295]
    cx = lambda w: (w["x0"] + w["x1"]) / 2
    assert any(abs(cx(w) - 194) < 3 for w in at("05"))
    yr = sorted((c for c in added_chars(pdf, 0) if 276 < c["top"] < 290 and 232 < c["x0"] < 275), key=lambda c: c["x0"])
    assert "".join(c["text"] for c in yr) == "1999"
    assert all(abs((c["x0"] + c["x1"]) / 2 - e) < 2 for c, e in zip(yr, L.YEAR_CELLS["nacimiento"]))   # un dígito por casilla
    # educación superior: primera fila de la tabla
    assert any(w["top"] > 579 and w["top"] < 596 for w in at("UN"))
    # último grado: 11 marcado con X sobre la casilla "11"
    x11 = [c for c in added_chars(pdf, 0) if c["text"] == "X" and 270 < c["x0"] < 282 and 460 < c["top"] < 476]
    assert x11, "falta X en el grado 11"
    # idioma: INGLÉS con B/MB/B en columnas habla/lee/escribe
    xs = sorted(round((c["x0"] + c["x1"]) / 2) for c in added_chars(pdf, 0) if c["text"] == "X" and 710 < c["top"] < 725)
    assert xs == [323, 391, 425] or [abs(a - b) <= 2 for a, b in zip(xs, [324, 392, 425])] == [True] * 3, xs
    w2, _ = words(pdf, 1)
    t2, _ = words(template_bytes(), 1)
    s2 = {(round(w["x0"]), round(w["top"]), w["text"]) for w in t2}
    add2 = [w for w in w2 if (round(w["x0"]), round(w["top"]), w["text"]) not in s2]
    assert any(w["text"] == "EMPRESA" and 60 <= w["x0"] < 70 and 228 < w["top"] < 246 for w in add2)    # bajo el rótulo EMPRESA O ENTIDAD
    assert any(w["text"] == "ANALISTA" or w["text"] == "CARGO" for w in add2)
    assert any(c["text"] == "X" and 385 < c["x0"] < 400 and 230 < c["top"] < 245 for c in added_chars(pdf, 1))   # PRIVADA marcada


def test_espacios_de_firma_y_rrhh_no_se_completan(client, alice):
    fill(client, alice, n_work=3)
    pdf = get_pdf(client, alice)
    # Página 3: solo pueden aparecer 8 números nuevos dentro de la tabla de tiempo (sección 4). Nada en secciones 5 y 6.
    ow, page = words(pdf, 2)
    tw, _ = words(template_bytes(), 2)
    tset = {(round(w["x0"]), round(w["top"]), w["text"]) for w in tw}
    added = [w for w in ow if (round(w["x0"]), round(w["top"]), w["text"]) not in tset]
    assert len(added) == 8
    assert all(150 < w["top"] < 290 and 350 < w["x0"] < 500 for w in added), [(w["text"], w["x0"], w["top"]) for w in added]
    # sin ningún trazo nuevo (gráficos) sobre la página 3: la plantilla no ganó líneas/rectángulos
    with pdfplumber.open(io.BytesIO(template_bytes())) as t, pdfplumber.open(io.BytesIO(pdf)) as o:
        assert (len(o.pages[2].lines), len(o.pages[2].rects), len(o.pages[2].curves)) == (len(t.pages[2].lines), len(t.pages[2].rects), len(t.pages[2].curves))
    # Página 1: «ENTIDAD RECEPTORA» (caja arriba a la derecha) vacía
    w1, _ = words(pdf, 0)
    assert not [w for w in w1 if w["top"] < 135 and w["x0"] > 420 and w["text"] not in {"ENTIDAD", "RECEPTORA"}]


def test_tiempo_total_en_la_seccion_4(client, alice):
    client.post("/api/work", json=work_payload(fecha_ingreso="2020-01-01", fecha_retiro="2021-12-31"), headers=alice["headers"])   # 731 días => 2 años 0 meses
    pdf = get_pdf(client, alice)
    ow, _ = words(pdf, 2)
    tw, _ = words(template_bytes(), 2)
    tset = {(round(w["x0"]), round(w["top"]), w["text"]) for w in tw}
    added = {(round(w["top"]), round((w["x0"] + w["x1"]) / 2)): w["text"] for w in ow if (round(w["x0"]), round(w["top"]), w["text"]) not in tset}
    privado_row = [v for (top, x), v in added.items() if 210 < top < 225]
    assert privado_row == ["2", "0"]


def test_experiencias_adicionales_repiten_la_pagina_2(client, alice):
    fill(client, alice, n_work=6, n_edu=1)
    pdf = get_pdf(client, alice)
    assert len(PdfReader(io.BytesIO(pdf)).pages) == 4            # p1 + 2 copias de p2 + p3
    prev = client.get("/api/export/preview", headers=alice["headers"]).json()["warnings"]
    assert any("2 copias" in w for w in prev)


def test_advertencias_por_limites_de_la_plantilla(client, alice):
    client.get("/api/resume", headers=alice["headers"])
    for i in range(7):
        client.post("/api/education", json=edu_payload(nombre_estudios=f"E{i}"), headers=alice["headers"])
    langs = [{"idioma": n, "habla": "B", "lee": "B", "escribe": "B"} for n in ("Inglés", "Francés", "Alemán")]
    save(client, alice, 0, languages=langs)
    prev = client.get("/api/export/preview", headers=alice["headers"]).json()["warnings"]
    assert any("2 registro(s)" in w for w in prev) and any("1 idioma(s)" in w for w in prev)
    assert get_pdf(client, alice)


def test_usuario_sin_datos_exporta_formato_en_blanco(client, make_user):
    u = make_user()
    pdf = get_pdf(client, u)
    assert len(PdfReader(io.BytesIO(pdf)).pages) == 3


def test_exporta_solo_datos_del_propio_usuario(client, alice, bob):
    fill(client, alice)
    client.get("/api/resume", headers=bob["headers"])
    pdf = get_pdf(client, bob)
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)
    assert "PRUEBA" not in text and "1000000000" not in text
    assert client.get("/api/export/pdf").status_code == 401


def test_encabezados_de_descarga(client, alice):
    r = client.get("/api/export/pdf", headers=alice["headers"])
    assert r.headers["x-content-type-options"] == "nosniff" and "attachment" in r.headers["content-disposition"] and "no-store" in r.headers["cache-control"]


def test_texto_largo_no_desborda_su_casilla(client, alice):
    client.get("/api/resume", headers=alice["headers"])
    save(client, alice, 0, personal={"primer_apellido": "A" * 55, "nombres": "N" * 70})
    pdf = get_pdf(client, alice)
    ow, _ = words(pdf, 0)
    tw, _ = words(template_bytes(), 0)
    tset = {(round(w["x0"]), round(w["top"]), w["text"]) for w in tw}
    for w in (w for w in ow if (round(w["x0"]), round(w["top"]), w["text"]) not in tset and w["top"] < 190):
        assert w["x1"] <= 226 or w["x0"] >= 227       # el primer apellido no invade la casilla del segundo
        assert w["x1"] <= 570
