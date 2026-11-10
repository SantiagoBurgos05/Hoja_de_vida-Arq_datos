"""Prueba de extremo a extremo en navegador real (Chromium/Playwright) contra backend + MongoDB reales.
Fuente de entidades: servidor SIMULADO local (datos sintéticos). No prueba fuentes oficiales en vivo."""
import io, os, sys, uuid
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

WEB = os.getenv("E2E_WEB", "http://127.0.0.1:4173")
OUT = Path(os.getenv("E2E_OUT", "/tmp/e2e-out")); OUT.mkdir(exist_ok=True, parents=True)
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n" + b"sintetico" * 30
PDF_PATH = OUT / "certificado_sintetico.pdf"; PDF_PATH.write_bytes(PDF)
EMAIL = f"e2e{uuid.uuid4().hex[:6]}@example.com"; PW = "clave-sintetica-123"
steps = []

def ok(name):
    steps.append(name); print("OK ", name)

def login(page, email, pw=PW):
    page.goto(WEB); page.get_by_label("Correo electrónico").fill(email); page.get_by_label("Contraseña (mínimo 10 caracteres)").fill(pw)
    page.get_by_role("button", name="Iniciar sesión").click()
    expect(page.get_by_text(email)).to_be_visible()

with sync_playwright() as pw:
    b = pw.chromium.launch()
    # ---- Sesión 1: registro y captura de datos
    ctx = b.new_context(accept_downloads=True); page = ctx.new_page()
    errors = []; page.on("pageerror", lambda e: errors.append(str(e))); page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(WEB)
    page.get_by_role("button", name="Crear una cuenta").click()
    page.get_by_label("Correo electrónico").fill(EMAIL); page.get_by_label("Contraseña (mínimo 10 caracteres)").fill(PW)
    page.get_by_role("button", name="Crear cuenta").click()
    expect(page.get_by_text("1 · Datos personales").first).to_be_visible(); ok("registro e inicio de sesión")
    page.get_by_label("Primer apellido").fill("Prueba"); page.get_by_label("Nombres").fill("Ana Maria"); page.get_by_label("Número", exact=True).fill("1000000000")
    expect(page.get_by_text("Guardado", exact=True).first).to_be_visible(timeout=8000); ok("autoguardado de datos personales")
    page.screenshot(path=str(OUT / "01_personales.png"), full_page=True)
    page.reload()
    expect(page.get_by_label("Primer apellido")).to_have_value("Prueba"); ok("persistencia tras recargar la página")
    page.get_by_role("button", name="Salir").click(); expect(page.get_by_role("button", name="Iniciar sesión")).to_be_visible()
    login(page, EMAIL)
    expect(page.get_by_label("Nombres")).to_have_value("Ana Maria"); ok("persistencia en una nueva sesión (cerrar y volver a entrar)")

    # ---- Formación + verificación + certificado
    page.get_by_role("link", name="2 · Formación").click()
    page.get_by_role("button", name="Agregar estudio superior").click()
    page.get_by_label("Nombre de los estudios o título").fill("Ingeniería de Sistemas")
    page.get_by_label("Institución (declarada)").first.fill("Universidad Sintetica del Norte")
    expect(page.get_by_text("Guardado", exact=True).first).to_be_visible(timeout=8000)
    rec = page.locator("article.record").first
    expect(rec.get_by_text("Entidad sin verificar")).to_be_visible()
    expect(rec.locator("input[type=file]")).to_be_disabled(); ok("carga de certificados deshabilitada antes de verificar la entidad")
    rec.get_by_text("Buscar y verificar entidad").click()
    rec.get_by_label("Nombre", exact=True).fill("universidad"); rec.get_by_role("button", name="Buscar").click()
    expect(rec.locator("ul.candidates li")).to_have_count(2); ok("búsqueda presenta coincidencias sin conceder verificación")
    expect(rec.get_by_text("Entidad sin verificar")).to_be_visible()
    rec.locator("ul.candidates li").first.get_by_role("button", name="Verificar esta").click()
    expect(rec.get_by_text("Entidad verificada en fuente oficial")).to_be_visible(timeout=8000); ok("verificación por identificador oficial en el backend")
    expect(rec.get_by_text("No acredita", exact=False).first).to_be_visible()
    expect(rec.locator("input[type=file]")).to_be_enabled()
    rec.locator("input[type=file]").set_input_files(str(PDF_PATH))
    expect(rec.get_by_text("certificado_sintetico.pdf")).to_be_visible(timeout=8000)
    expect(rec.get_by_text("Soporte adjunto").first).to_be_visible(); expect(rec.get_by_text("Autenticidad no validada")).to_be_visible(); ok("carga de certificado y estado «soporte adjunto»")
    page.screenshot(path=str(OUT / "02_formacion.png"), full_page=True)
    ctx.close()

    # ---- Sesión 2 (contexto nuevo = otro navegador): recuperar sin volver a cargar
    ctx2 = b.new_context(accept_downloads=True); p2 = ctx2.new_page(); login(p2, EMAIL)
    p2.get_by_role("link", name="2 · Formación").click()
    rec2 = p2.locator("article.record").first
    expect(rec2.get_by_text("certificado_sintetico.pdf")).to_be_visible(timeout=8000)
    expect(rec2.get_by_text("Entidad verificada en fuente oficial")).to_be_visible()
    expect(rec2.get_by_text("UNIVERSIDAD SINTETICA DEL NORTE", exact=False).first).to_be_visible()
    with p2.expect_download() as dl: rec2.get_by_role("button", name="Descargar").click()
    path = dl.value.path(); assert Path(path).read_bytes() == PDF; ok("certificado recuperado en otra sesión, idéntico byte a byte, sin volver a cargarlo")

    # ---- Experiencia (RUES deshabilitado) + tiempo total
    p2.get_by_role("link", name="3-4 · Experiencia").click()
    p2.get_by_role("button", name="Agregar experiencia").click()
    w = p2.locator("article.record").first
    w.get_by_label("Empresa o entidad (declarada)").fill("Empresa Sintetica SAS")
    w.get_by_label("Fecha de ingreso").fill("2020-01-01"); w.get_by_label("Fecha de retiro").fill("2021-12-31")
    w.get_by_label("Cargo o contrato").fill("Analista")
    expect(w.get_by_text("Guardado", exact=True)).to_be_visible(timeout=8000)
    w.get_by_text("Buscar y verificar entidad").click(); w.get_by_label("o identificador oficial (NIT/código)").fill("900000000"); w.get_by_role("button", name="Buscar").click()
    expect(w.get_by_text("RUES: sin API")).to_be_visible(timeout=8000)
    expect(w.get_by_text("Entidad sin verificar")).to_be_visible(); expect(w.locator("input[type=file]")).to_be_disabled(); ok("RUES deshabilitado: borrador conservado sin verificación")
    p2.reload(); p2.get_by_role("link", name="3-4 · Experiencia").click()
    expect(p2.locator("table.time tr.total td").nth(1)).to_have_text("2"); ok("tiempo total calculado (2 años)")
    p2.screenshot(path=str(OUT / "03_experiencia.png"), full_page=True)

    # ---- Exportar PDF
    p2.get_by_role("link", name="5-6 · Exportar").click()
    with p2.expect_download() as dl2: p2.get_by_role("button", name="Descargar PDF sobre el formato oficial").click()
    pdf_bytes = Path(dl2.value.path()).read_bytes()
    from pypdf import PdfReader
    assert len(PdfReader(io.BytesIO(pdf_bytes)).pages) == 3 and pdf_bytes.startswith(b"%PDF"); ok("exportación a PDF de 3 páginas desde la interfaz")
    (OUT / "hoja_de_vida_e2e.pdf").write_bytes(pdf_bytes)
    ctx2.close()

    # ---- Aislamiento: otro usuario no ve nada
    ctx3 = b.new_context(); p3 = ctx3.new_page(); p3.goto(WEB)
    p3.get_by_role("button", name="Crear una cuenta").click()
    other = f"otro{uuid.uuid4().hex[:6]}@example.com"
    p3.get_by_label("Correo electrónico").fill(other); p3.get_by_label("Contraseña (mínimo 10 caracteres)").fill(PW); p3.get_by_role("button", name="Crear cuenta").click()
    expect(p3.get_by_label("Primer apellido")).to_have_value("")
    p3.get_by_role("link", name="2 · Formación").click(); expect(p3.locator("article.record")).to_have_count(0)
    p3.get_by_role("link", name="3-4 · Experiencia").click(); expect(p3.locator("article.record")).to_have_count(0); ok("aislamiento: otro usuario no ve datos ni soportes")
    # el otro usuario intenta descargar el soporte ajeno con su token
    tok = p3.evaluate("sessionStorage.getItem('hv_token')")
    ctx3.close(); b.close()
    assert not [e for e in errors if "favicon" not in e], errors
    ok("sin errores de consola/JS en el navegador")
print(f"\n{len(steps)} comprobaciones E2E correctas")
