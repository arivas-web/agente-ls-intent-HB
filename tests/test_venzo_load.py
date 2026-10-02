from datetime import date
from vt.venzo.load import map_row, normalize_status, parse_date, read_rows

COLS = {"cif": "NIF", "domain": "Web", "name": "Cliente", "opportunity_id": "Ref", "stage": "Fase", "status": "Estado",
        "loss_reason": "Motivo", "opened_at": "Alta", "closed_at": "Cierre", "last_activity": "Última", "notes": "Notas"}


def test_csv_con_punto_y_coma_y_bom(tmp_path):
    f = tmp_path / "v.csv"
    f.write_text("﻿Ref;Cliente;NIF\n1;Acme SL;B123\n2;Beta;B456\n", encoding="utf-8")
    rows = read_rows(str(f))
    assert len(rows) == 2 and rows[0]["Cliente"] == "Acme SL" and rows[0]["Ref"] == "1"


def test_mapeo_y_fechas():
    raw = {"NIF": "B123", "Web": "acme.com", "Cliente": "Acme", "Ref": "9", "Fase": "Propuesta", "Estado": "Perdida",
           "Motivo": "Precio", "Alta": "05/03/2026", "Cierre": "2026-04-01", "Última": "10/04/26", "Notas": "x"}
    r = map_row(raw, COLS, {"perdida": "perdida", "ganada": "ganada"})
    assert r["status_norm"] == "perdida" and r["opened_at"] == date(2026, 3, 5) and r["closed_at"] == date(2026, 4, 1)
    assert r["last_management_at"] == date(2026, 4, 10) and r["cif"] == "B123"
    assert parse_date("no es fecha") is None and normalize_status("???", {"x": "abierta"}) is None
