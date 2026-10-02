from datetime import date
from vt.ingest.outcomes import normalize_outcome
from vt.rates import by_dimension, compute_rates, lift, propose_weights, rate

D = date


def A(c, grp="puntuada", sdr="Emma", code="A1", tm="Transitario PYME"):
    return {"company": c, "sdr": sdr, "code": code, "group": grp, "target_market": tm, "assigned_at": D(2026, 10, 5)}


OUT = [{"company": "1", "outcome": "no_contesta", "at": D(2026, 10, 6)},
       {"company": "1", "outcome": "reunion", "at": D(2026, 10, 9)},
       {"company": "2", "outcome": "no_contesta", "at": D(2026, 10, 6)},
       {"company": "3", "outcome": "mal_timing", "at": D(2026, 10, 7)},
       {"company": "0", "outcome": "reunion", "at": D(2026, 9, 1)}]          # anterior a la asignación: no cuenta
OPP = [{"company": "1", "status_norm": "ganada", "opened_at": D(2026, 10, 15), "closed_at": D(2026, 11, 1)},
       {"company": "3", "status_norm": "perdida", "opened_at": D(2026, 10, 20), "closed_at": None}]


def test_tasas_sobre_cuentas_y_llamadas():
    r = compute_rates([A("1"), A("2"), A("3"), A("4")], OUT, OPP, [])
    sc = r["sobre_cuentas"]
    assert sc["contacto"] == rate(2, 4) and sc["reunion"] == rate(1, 4) and sc["oportunidad"] == rate(2, 4)
    assert sc["ganada"] == rate(1, 4) and sc["perdida"] == rate(1, 4)
    assert r["sobre_llamadas"]["contacto"] == rate(2, 4) and r["sobre_llamadas"]["reunion"] == rate(1, 4)
    assert r["dias_asignacion_a_reunion"] == 4 and r["dias_asignacion_a_oportunidad"] == 12.5


def test_alerta_a_reunion():
    al = [{"company": "1", "sent_at": D(2026, 10, 7)}, {"company": "3", "sent_at": D(2026, 10, 7)}]
    assert compute_rates([A("1"), A("3")], OUT, OPP, al)["alerta_a_reunion"] == rate(1, 2)


def test_denominador_cero_es_none():
    assert compute_rates([], [], [], [])["sobre_cuentas"]["reunion"]["pct"] is None


def test_lift_y_desgloses():
    asg = [A("1"), A("2"), A("5", "control"), A("6", "control", sdr="Laura", code="C1")]
    out = OUT + [{"company": "5", "outcome": "reunion", "at": D(2026, 10, 8)}]
    l = lift(asg, out, OPP, [])
    assert l["puntuada"] == rate(1, 2) and l["control"] == rate(1, 2) and l["lift"] == 1.0
    assert set(by_dimension(asg, out, OPP, [], "sdr")) == {"Emma", "Laura"}
    assert set(by_dimension(asg, out, OPP, [], "code")) == {"A1", "C1"}


def test_propuestas_solo_proponen():
    props = propose_weights({"precios": 6, "empresa": 1}, {"precios": 3, "empresa": 20}, 10, 100)
    assert {(p["signal"], p["action"]) for p in props} == {("precios", "subir"), ("empresa", "bajar")}
    assert propose_weights({"x": 1}, {"x": 1}, 10, 100) == []          # muestra pequeña


def test_normalizar_resultado_de_llamada():
    assert normalize_outcome("reunión") == "reunion" and normalize_outcome("Mal timing") == "mal_timing"
    assert normalize_outcome("ya tiene proveedor") == "ya_tiene_proveedor" and normalize_outcome("otra cosa") is None
