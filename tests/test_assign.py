from collections import Counter
from vt.config import load
from vt.assign.build import balance, build_draft, is_eligible, rank_candidates
from vt.timeguard import at_hour, in_window
from datetime import datetime
from zoneinfo import ZoneInfo

M = load("priority_matrix")
CFG = load("assignment")


def row(i, code, vel=0.0, fit=50.0, status="Nurturing", tier="A", eng=0.0, tipo=None):
    return {"hs_id": str(i), "code": code, "velocity": vel, "fit": fit, "fit_tier": tier, "engagement": eng,
            "status": status, "tipo_de_contacto": tipo}


def test_elegibilidad():
    assert not is_eligible(row(1, "A1", status="Client"), CFG)
    assert not is_eligible(row(1, "A1", status="Meeting"), CFG)
    assert is_eligible(row(1, "A1", status=None), CFG)
    assert not is_eligible(row(1, "A1", tipo="Competencia"), CFG)
    assert not is_eligible(row(1, "A1"), CFG, open_opportunity_ids={"1"})   # oportunidad abierta en Venzo


def test_orden_codigo_velocidad_fit():
    rows = [row(1, "A3", 9), row(2, "B1", 1), row(3, "A1", 1, fit=60), row(4, "A1", 5, fit=40), row(5, "C3"),
            row(6, "A1", 5, fit=70)]
    assert [r["hs_id"] for r in rank_candidates(rows, M)] == ["6", "4", "3", "2", "1"]


def test_balance_por_nivel():
    rows = [row(i, "A1") for i in range(5)] + [row(10 + i, "A2") for i in range(5)] + [row(20 + i, "B1") for i in range(4)]
    out = balance(rows, ["Emma", "Laura"], 7)
    for code in ("A1", "A2", "B1"):
        a, b = (sum(1 for r in out[s] if r["code"] == code) for s in ("Emma", "Laura"))
        assert abs(a - b) <= 1
    assert len(out["Emma"]) == len(out["Laura"]) == 7


def test_borrador_completo_control_y_exclusiones():
    rows = [row(i, "A3", fit=90 - i * 0.01) for i in range(200)]
    rows += [row(300 + i, "A1", 3) for i in range(3)] + [row(400, "A1", status="Client")]
    inactive = {str(i) for i in range(100, 200)}
    asg, cands = build_draft(rows, CFG, M, seed="vt-2026-10-05", inactive_ids=inactive)
    assert Counter(a["sdr"] for a in asg) == {"Emma": 10, "Laura": 10}
    ctrl = [a for a in asg if a["is_control"]]
    assert len(ctrl) == 4 and all(a["hs_id"] in inactive and a["origin"] == "control" for a in ctrl)
    assert Counter(a["sdr"] for a in ctrl) == {"Emma": 2, "Laura": 2}
    assert "400" not in {a["hs_id"] for a in asg}                       # cliente excluido
    assert {"300", "301", "302"} <= {a["hs_id"] for a in asg}            # A1 siempre dentro
    assert len(cands) == 60 and not ({c["hs_id"] for c in cands} & {a["hs_id"] for a in asg})
    asg2, _ = build_draft(rows, CFG, M, seed="vt-2026-10-05", inactive_ids=inactive)
    assert asg == asg2                                                    # sorteo reproducible


def test_horarios_madrid():
    mad = ZoneInfo("Europe/Madrid")
    lunes_verano = datetime(2026, 10, 5, 8, 5, tzinfo=mad)               # lunes 08:05 CEST
    assert at_hour("mon", 8, lunes_verano) and not at_hour("mon", 7, lunes_verano)
    # El mismo instante UTC en invierno (CET): lunes 08:05 Madrid = 07:05 UTC
    invierno = datetime(2026, 11, 2, 7, 5, tzinfo=ZoneInfo("UTC"))
    assert at_hour("mon", 8, invierno)
    assert in_window(["mon", "tue"], "09:00", "18:00", datetime(2026, 10, 6, 17, 59, tzinfo=mad))
    assert not in_window(["mon", "tue"], "09:00", "18:00", datetime(2026, 10, 6, 18, 0, tzinfo=mad))
    assert not in_window(["mon"], "09:00", "18:00", datetime(2026, 10, 10, 10, 0, tzinfo=mad))   # sábado
