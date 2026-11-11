#!/usr/bin/env python3
"""Comprobación EN VIVO de las fuentes educativas contra datos.gov.co (manual; requiere internet).

Para cada fuente: busca por nombre (y municipio), toma la primera coincidencia y la verifica por su
identificador oficial con el mismo conector que usa la API. Comprueba además que un identificador
inexistente no verifique. Guarda la evidencia en .local-checks/sources/ (no se versiona: contiene
datos institucionales públicos reales).

Uso:  python scripts/check_sources.py
Salida 0 si todas las fuentes responden como se espera; 1 si alguna falla.
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.modules.organizations.connectors import registry  # noqa: E402
from app.modules.organizations.connectors.base import ConnectorError  # noqa: E402

CASES = [
    # (fuente, nombre, municipio, identificador inexistente)
    ("snies", "minuto de dios", "bogota", "999999"),
    ("siet", "ensenanza", "bogota", "99999999"),
    ("due", "san bartolome", "bogota", "999999999999"),
]


def main() -> int:
    out = ROOT / ".local-checks" / "sources"
    out.mkdir(parents=True, exist_ok=True)
    report, ok_all = [], True
    for source, name, muni, missing in CASES:
        c = registry.make(source)
        item = {"source": source, "dataset": c.dataset, "query": name, "municipio": muni}
        try:
            t = time.perf_counter()
            cands = c.search(name, muni, None)
            item["search_ms"] = round((time.perf_counter() - t) * 1000)
            item["candidates"] = [x.to_dict() for x in cands]
            if not cands:
                raise AssertionError("la búsqueda no devolvió coincidencias")
            first = cands[0]
            matches, evidence = c.get_by_official_id(first.official_id)
            item["verify"] = {"official_id": first.official_id, "matches": [m.to_dict() for m in matches],
                              "evidence_bytes": len(evidence.get("raw", ""))}
            if len(matches) != 1 or matches[0].official_id != first.official_id:
                raise AssertionError(f"verificación por identificador devolvió {len(matches)} coincidencias")
            none, _ = c.get_by_official_id(missing)
            item["missing_id"] = {"official_id": missing, "matches": len(none)}
            if none:
                raise AssertionError("un identificador inexistente devolvió coincidencias")
            item["ok"] = True
            print(f"OK    {source:6} {len(cands)} coincidencias; verificado {first.official_id} «{matches[0].name}» "
                  f"({matches[0].municipio}) — {matches[0].estado_registral}")
        except (ConnectorError, AssertionError) as e:
            ok_all = False
            item["ok"], item["error"] = False, str(e)
            print(f"FALLA {source:6} {e}")
        report.append(item)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    path = out / f"sources-{stamp}.json"
    path.write_text(json.dumps({"at": stamp, "ok": ok_all, "results": report}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Evidencia: {path.relative_to(ROOT)}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
