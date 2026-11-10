"""Exportación a PDF sobre la plantilla oficial.

- La plantilla original se conserva: se superpone texto con reportlab y se fusiona con pypdf.
- NO se completan: Entidad receptora, declaración SI/NO de inhabilidad, ciudad y fecha de diligenciamiento,
  firma (sección 5) ni observaciones del jefe de Recursos Humanos (sección 6).
- Experiencia: se repite la página 2 por cada 4 experiencias («imprima nuevamente esta hoja»).
- Límites de la plantilla (se informan como advertencias, no se ocultan): 5 filas de educación superior y 2 de idiomas.
"""
from __future__ import annotations
import io
from datetime import date
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from ...core.db import get_db
from ..resume import service as resume
from ..resume.timecalc import summarize
from . import layout as L

TEMPLATE = Path(__file__).resolve().parents[2] / "export" / "templates" / "fuhv_persona_natural.pdf"
FONT, FONT_B = "Helvetica", "Helvetica-Bold"


class Pen:
    def __init__(self, c: canvas.Canvas):
        self.c = c

    def text(self, x, y_top, s, maxw=None, size=8, font=FONT, align="l"):
        s = "" if s is None else str(s)
        if not s:
            return
        while maxw and stringWidth(s, font, size) > maxw and size > 4.5:
            size -= 0.25
        if maxw and stringWidth(s, font, size) > maxw:   # aún no cabe: recortar con elipsis
            while s and stringWidth(s + "…", font, size) > maxw:
                s = s[:-1]
            s += "…"
        self.c.setFont(font, size)
        y = L.H - y_top
        if align == "c":
            self.c.drawCentredString(x, y, s)
        else:
            self.c.drawString(x, y, s)

    def mark(self, x, y_top, size=9):
        self.text(x, y_top + size * 0.33, "X", size=size, font=FONT_B, align="c")

    def year(self, cells, year, y):
        """Un dígito por casilla (las casillas de año tienen divisiones que no deben cruzarse)."""
        for cx, ch in zip(cells, str(year)):
            self.text(cx, y, ch, size=8, align="c")

    def wrapped(self, x, row_top, s, maxw, size=6.3):
        """Hasta 2 líneas dentro de una fila de 17,5 pt; si aún no cabe, recorta con elipsis."""
        s = (s or "").strip()
        if not s:
            return
        if stringWidth(s, FONT, 7) <= maxw:
            self.text(x, row_top + 11.5, s, maxw, size=7)
            return
        words, l1, l2 = s.split(), "", ""
        for w in words:
            cand = (l1 + " " + w).strip()
            if not l2 and stringWidth(cand, FONT, size) <= maxw:
                l1 = cand
            else:
                l2 = (l2 + " " + w).strip()
        self.text(x, row_top + 7.2, l1, maxw, size=size)
        self.text(x, row_top + 14.2, l2, maxw, size=size)


def _upper(s):
    return (s or "").upper()


def _d(iso):
    return date.fromisoformat(iso) if iso else None


def collect(user_id) -> dict:
    db = get_db()
    r = resume.get_or_create_resume(user_id)
    return {"resume": r, "education": resume.list_records(user_id, "education_higher"),
            "work": resume.list_records(user_id, "work"), "orgs": {o["_id"]: o for o in db.organizations.find({})}}


def warnings_for(data: dict) -> list[str]:
    w = []
    if len(data["education"]) > L.EDU_MAX_ROWS:
        w.append(f"La plantilla oficial tiene {L.EDU_MAX_ROWS} filas de educación superior; {len(data['education']) - L.EDU_MAX_ROWS} registro(s) no caben y NO se imprimen.")
    if len(data["resume"].get("languages", [])) > L.LANG_MAX_ROWS:
        w.append(f"La plantilla oficial tiene {L.LANG_MAX_ROWS} filas de idiomas; {len(data['resume']['languages']) - L.LANG_MAX_ROWS} idioma(s) NO se imprimen.")
    n = len(data["work"])
    if n > L.EXP_MAX:
        w.append(f"Se imprimirán {-(-n // L.EXP_MAX)} copias de la página 2 (4 experiencias por hoja).")
    return w


def _page1(p: Pen, data: dict):
    r = data["resume"]
    per, eb = r.get("personal", {}), r.get("education_basic", {})
    for k in ("primer_apellido", "segundo_apellido", "nombres"):
        x, y, w = L.P1_TEXT[k]
        p.text(x, y, _upper(per.get(k)), w)
    if per.get("tipo_documento"):
        p.mark(*L.P1_MARKS[("tipo_documento", per["tipo_documento"])])
    x, y, w = L.P1_TEXT["numero_documento"]; p.text(x, y, per.get("numero_documento"), w)
    if per.get("sexo"):
        p.mark(*L.P1_MARKS[("sexo", per["sexo"])])
    if per.get("nacionalidad"):
        p.mark(*L.P1_MARKS[("nacionalidad", per["nacionalidad"])])
    x, y, w = L.P1_TEXT["pais_nacionalidad"]; p.text(x, y, _upper(per.get("pais_nacionalidad")), w)
    lm = per.get("libreta_militar") or {}
    if lm.get("clase"):
        p.mark(*L.P1_MARKS[("libreta", lm["clase"])])
    x, y, w = L.P1_TEXT["libreta_numero"]; p.text(x, y, lm.get("numero"), w)
    x, y, w = L.P1_TEXT["libreta_dm"]; p.text(x, y, lm.get("dm"), w)
    nac = per.get("nacimiento") or {}
    f = _d(nac.get("fecha"))
    if f:
        p.text(L.P1_DATE["dia"][0], L.P1_DATE["dia"][1], f"{f.day:02d}", size=8, align="c")
        p.text(L.P1_DATE["mes"][0], L.P1_DATE["mes"][1], f"{f.month:02d}", size=8, align="c")
        p.year(L.YEAR_CELLS["nacimiento"], f.year, L.P1_DATE["anio"][1])
    for k, key in (("nac_pais", "pais"), ("nac_depto", "departamento"), ("nac_municipio", "municipio")):
        x, y, w = L.P1_TEXT[k]; p.text(x, y, _upper(nac.get(key)), w)
    cor = per.get("correspondencia") or {}
    for k, key in (("dir_direccion", "direccion"), ("dir_pais", "pais"), ("dir_depto", "departamento"),
                   ("dir_municipio", "municipio"), ("dir_telefono", "telefono")):
        x, y, w = L.P1_TEXT[k]; p.text(x, y, _upper(cor.get(key)) if key != "telefono" else cor.get(key), w)
    x, y, w = L.P1_TEXT["dir_email"]; p.text(x, y, cor.get("email"), w, size=7)

    # Educación básica y media
    g = eb.get("ultimo_grado")
    if g in L.GRADE_X:
        p.mark(L.GRADE_X[g], 468)
    x, y, w = L.TITULO_BASICA; p.text(x, y, _upper(eb.get("titulo_obtenido")), w, size=7)
    fg = eb.get("fecha_grado") or {}
    if fg.get("mes"):
        p.text(L.GRADO_MES[0], L.GRADO_MES[1], f"{fg['mes']:02d}", align="c")
    if fg.get("anio"):
        p.year(L.YEAR_CELLS["grado"], fg["anio"], L.GRADO_ANIO[1])

    # Educación superior (orden cronológico por fecha de terminación)
    def key(e):
        t = e.get("terminacion") or {}
        return (t.get("anio") or 0, t.get("mes") or 0)
    for i, e in enumerate(sorted(data["education"], key=key)[: L.EDU_MAX_ROWS]):
        base = L.EDU_ROW_TOP[i] + L.EDU_ROW_BASE
        c = L.EDU
        p.text(c["modalidad"][0], base, e.get("modalidad"), size=8, align="c")
        if e.get("semestres_aprobados") is not None:
            p.text(c["semestres"][0], base, str(e["semestres_aprobados"]), size=8, align="c")
        if e.get("graduado") is True:
            p.mark(c["si"][0], base - 3)
        elif e.get("graduado") is False:
            p.mark(c["no"][0], base - 3)
        org = data["orgs"].get(e.get("organization_id"))
        title = e.get("nombre_estudios", "")
        inst = (org["name"] if org else e.get("institucion_declarada")) or ""
        p.wrapped(c["nombre"][0], L.EDU_ROW_TOP[i], _upper(f"{title} - {inst}" if inst else title), c["nombre"][2])
        t = e.get("terminacion") or {}
        if t.get("mes"):
            p.text(c["mes"][0], base, f"{t['mes']:02d}", size=8, align="c")
        if t.get("anio"):
            p.year(L.YEAR_CELLS["edu"], t["anio"], base)
        p.text(c["tarjeta"][0], base, e.get("tarjeta_profesional"), c["tarjeta"][2], size=7)

    # Idiomas (la plantilla solo trae 2 filas)
    for i, lg in enumerate(r.get("languages", [])[: L.LANG_MAX_ROWS]):
        base = L.LANG_ROW_BASE[i]
        p.text(L.LANG_NAME[0], base, _upper(lg["idioma"]), L.LANG_NAME[1], size=8)
        for col in ("habla", "lee", "escribe"):
            p.text(L.LANG_COLS[col][lg[col]], base, "X", size=8, font=FONT_B, align="c")


def _page2(p: Pen, chunk: list[dict], first_is_current_slot: bool, data: dict):
    for i, w in enumerate(chunk):
        top = L.EXP_BLOCK_TOP[i]
        e = L.EXP
        org = data["orgs"].get(w.get("organization_id"))
        name = (org["name"] if org else w.get("empresa_declarada")) or ""
        p.text(e["empresa"][0], top + e["empresa"][1], _upper(name), e["empresa"][2], size=8)
        if w.get("tipo_entidad") == "publica":
            p.mark(e["publica"][0], top + e["publica"][1] - 3)
        elif w.get("tipo_entidad") == "privada":
            p.mark(e["privada"][0], top + e["privada"][1] - 3)
        for k, key in (("pais", "pais"), ("departamento", "departamento"), ("municipio", "municipio"),
                       ("dependencia", "dependencia"), ("direccion", "direccion"), ("cargo", "cargo")):
            p.text(e[k][0], top + e[k][1], _upper(w.get(key)), e[k][2], size=8)
        p.text(e["correo"][0], top + e["correo"][1], w.get("correo_entidad"), e["correo"][2], size=7)
        p.text(e["telefonos"][0], top + e["telefonos"][1], w.get("telefonos"), e["telefonos"][2], size=8)
        base = top + L.EXP_DATE_BASE
        di, dr = _d(w.get("fecha_ingreso")), _d(w.get("fecha_retiro"))
        X = L.EXP_DATE_X
        if di:
            p.text(X["ing_dia"], base, f"{di.day:02d}", align="c"); p.text(X["ing_mes"], base, f"{di.month:02d}", align="c")
            p.year(L.YEAR_CELLS["ing"], di.year, base)
        if dr and not w.get("es_actual"):
            p.text(X["ret_dia"], base, f"{dr.day:02d}", align="c"); p.text(X["ret_mes"], base, f"{dr.month:02d}", align="c")
            p.year(L.YEAR_CELLS["ret"], dr.year, base)


def _page3(p: Pen, data: dict):
    s = summarize(data["work"])
    for cat, base in L.TIME_ROW_BASE.items():
        v = s[cat]
        p.text(L.TIME_X["anios"], base, str(v["anios"]), size=9, align="c")
        p.text(L.TIME_X["meses"], base, str(v["meses"]), size=9, align="c")
    # Secciones 5 y 6 (declaración, ciudad/fecha, firma, observaciones RR.HH.) NO se tocan.


def _overlay(fn) -> PdfReader:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(612, 792))
    fn(Pen(c))
    c.showPage()
    c.save()
    buf.seek(0)
    return PdfReader(buf)


def _add(writer: PdfWriter, template_page_idx: int, overlay_fn) -> None:
    """Cada página se toma de un lector nuevo (la página 2 puede repetirse) y se adjunta al writer ANTES de fusionar."""
    page = writer.add_page(PdfReader(str(TEMPLATE)).pages[template_page_idx])
    page.merge_page(_overlay(overlay_fn).pages[0])


def build_pdf(user_id) -> tuple[bytes, list[str]]:
    data = collect(user_id)
    w = PdfWriter()
    _add(w, 0, lambda p: _page1(p, data))
    work = sorted(data["work"], key=lambda x: (not x.get("es_actual", False), _neg_date(x)))
    chunks = [work[i:i + L.EXP_MAX] for i in range(0, max(len(work), 1), L.EXP_MAX)] or [[]]
    for ch in chunks:
        _add(w, 1, lambda p, ch=ch: _page2(p, ch, True, data))
    _add(w, 2, lambda p: _page3(p, data))
    out = io.BytesIO()
    w.write(out)
    return out.getvalue(), warnings_for(data)


def _neg_date(w):
    d = w.get("fecha_ingreso") or "0001-01-01"
    return tuple(-int(x) for x in d.split("-"))   # más reciente primero (orden cronológico inverso; el actual va al inicio)
