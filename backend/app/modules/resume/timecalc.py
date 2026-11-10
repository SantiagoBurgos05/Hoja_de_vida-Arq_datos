"""Cálculo del tiempo total de experiencia (sección 4 del formato).

Reglas (ver docs/arquitectura.md §Tiempo total):
- Intervalo semiabierto [ingreso, fin). Fecha de retiro: el último día laborado es el día de retiro,
  por eso fin = retiro + 1 día. Si es_actual: fin = fecha de corte (hoy) + 1 día.
- Se une el solapamiento por categoría y de forma global (un día cuenta una sola vez).
- Convención de conversión: 365 días = 1 año, 30 días = 1 mes (resto). Es una *estimación académica*,
  no una certificación legal de tiempo de servicio.
"""
from __future__ import annotations
from datetime import date, timedelta
from typing import Iterable

CATS = ("servidor_publico", "empleado_privado", "independiente")


def _interval(rec: dict, today: date) -> tuple[date, date] | None:
    ini = rec.get("fecha_ingreso")
    if not ini:
        return None
    ini = date.fromisoformat(ini) if isinstance(ini, str) else ini
    if rec.get("es_actual"):
        fin = today + timedelta(days=1)
    else:
        ret = rec.get("fecha_retiro")
        if not ret:
            return None
        ret = date.fromisoformat(ret) if isinstance(ret, str) else ret
        fin = ret + timedelta(days=1)
    if fin <= ini:
        return None
    return ini, fin


def _union_days(intervals: Iterable[tuple[date, date]]) -> int:
    items = sorted(intervals)
    total, cur_s, cur_e = 0, None, None
    for s, e in items:
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                total += (cur_e - cur_s).days
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None:
        total += (cur_e - cur_s).days
    return total


def to_years_months(days: int) -> dict:
    return {"dias": days, "anios": days // 365, "meses": (days % 365) // 30}


def summarize(records: list[dict], today: date | None = None) -> dict:
    today = today or date.today()
    per: dict[str, list] = {c: [] for c in CATS}
    ignored = 0
    for r in records:
        iv = _interval(r, today)
        cat = r.get("categoria_tiempo")
        if iv is None or cat not in per:
            ignored += 1
            continue
        per[cat].append(iv)
    out = {c: to_years_months(_union_days(v)) for c, v in per.items()}
    out["total"] = to_years_months(_union_days([iv for v in per.values() for iv in v]))
    out["registros_ignorados"] = ignored
    out["nota"] = "Estimación académica (365 días = 1 año; 30 días = 1 mes). No sustituye certificación de tiempo de servicio."
    return out
