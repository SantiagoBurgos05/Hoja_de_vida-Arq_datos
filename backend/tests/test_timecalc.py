from datetime import date
from app.modules.resume.timecalc import summarize, to_years_months


def w(cat, ini, ret=None, actual=False):
    return {"categoria_tiempo": cat, "fecha_ingreso": ini, "fecha_retiro": ret, "es_actual": actual}


def test_retiro_cuenta_dia_inclusive():
    s = summarize([w("empleado_privado", "2020-01-01", "2020-01-31")])
    assert s["empleado_privado"]["dias"] == 31


def test_un_anio_exacto_no_cuenta_anio_bisiesto_como_mas():
    s = summarize([w("empleado_privado", "2021-01-01", "2021-12-31")])
    assert s["empleado_privado"]["dias"] == 365 and s["empleado_privado"]["anios"] == 1 and s["empleado_privado"]["meses"] == 0


def test_solapamiento_misma_categoria_no_se_suma_dos_veces():
    s = summarize([w("independiente", "2020-01-01", "2020-06-30"), w("independiente", "2020-04-01", "2020-12-31")])
    assert s["independiente"]["dias"] == 366      # 2020 bisiesto: 1-ene..31-dic


def test_solapamiento_entre_categorias_total_global_une():
    s = summarize([w("servidor_publico", "2020-01-01", "2020-12-31"), w("independiente", "2020-07-01", "2021-06-30")])
    assert s["servidor_publico"]["dias"] == 366 and s["independiente"]["dias"] == 365
    assert s["total"]["dias"] == 366 + 181          # 2020-01-01 .. 2021-06-30 (union), 1-ene-2020..30-jun-2021
    # comprobación independiente: 2020-01-01..2021-06-30 inclusive = 366 + 181 días
    assert (date(2021, 7, 1) - date(2020, 1, 1)).days == s["total"]["dias"]


def test_actual_usa_fecha_de_corte_y_sin_fechas_se_ignora():
    s = summarize([w("empleado_privado", "2024-01-01", None, True), w("independiente", None, None)], today=date(2024, 1, 10))
    assert s["empleado_privado"]["dias"] == 10 and s["registros_ignorados"] == 1


def test_retiro_antes_de_ingreso_se_ignora():
    assert summarize([w("independiente", "2022-05-01", "2022-04-01")])["total"]["dias"] == 0


def test_conversion_y_nota_de_estimacion():
    assert to_years_months(400) == {"dias": 400, "anios": 1, "meses": 1}
    assert "Estimación" in summarize([])["nota"]
