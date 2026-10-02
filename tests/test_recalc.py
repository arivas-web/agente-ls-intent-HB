from datetime import datetime, timedelta, timezone
from vt.config import load
from vt.recalc import compute_company
from vt.scoring.signals import Signal

NOW = datetime(2026, 10, 2, 12, tzinfo=timezone.utc)
CFG = {k: load(v) for k, v in {"fit": "fit", "eng": "engagement", "int": "intent", "persona": "persona",
                               "matrix": "priority_matrix", "url": "url_scoring"}.items()}


def ct(i, cargo="CEO"):
    return {"hs_id": i, "cargo_icp": cargo, "phones": ["600"], "email": "a@b.es", "email_bounced": False,
            "linkedin_url": "", "excluded": False}


def test_cuenta_a1_completa():
    co = {"target_market": "Transitario PYME", "proveedor": "Excel", "pais": "España"}
    s = [Signal("1", "intent", "web_visit", NOW - timedelta(hours=3), 20, "/precios/", "k", {"rule_id": "precios"}),
         Signal("1", "intent", "web_visit", NOW - timedelta(hours=4), 15, "/demo-visual-trans/", "k", {"rule_id": "demo"}),
         Signal("1", "intent", "web_visit", NOW - timedelta(hours=5), 8, "/productos/suite/", "k", {"rule_id": "producto_principal"}),
         Signal("1", "engagement", "content_download", NOW, 8, "guia", "k")]
    r = compute_company(co, [ct("1"), ct("2", "Operativo")], s, CFG, NOW)
    assert r["fit"]["tier"] == "A" and r["intent"]["tier"] == 1 and r["priority"] == "A1"
    assert r["action"] == "llamar" and r["best_contact"] == "1" and not r["missing_decision_maker"]


def test_sin_senales_ni_contactos():
    co = {"target_market": "Courier", "proveedor": None, "pais": None}
    r = compute_company(co, [], [], CFG, NOW)
    assert r["priority"] == "C3" and r["action"] == "fuera" and r["missing_decision_maker"] is True


def test_movimiento_es_el_maximo_de_intencion_y_engagement():
    co = {"target_market": "Transitario PYME", "proveedor": "Excel", "pais": "España"}
    # Muchas descargas de contenido (engagement) pero ninguna visita de decisión (intención = 0).
    s = [Signal(str(i), "engagement", "content_download", NOW, 8, f"d{i}", "k") for i in range(4)]
    cts = [ct(str(i)) for i in range(4)]
    r = compute_company(co, cts, s, CFG, NOW)
    assert r["intent"]["score"] == 0 and r["engagement"]["score"] > 0
    assert r["movement"]["score"] == r["engagement"]["score"] and r["priority"] == "A1"   # con movimiento=max sube de A3 a A1
    cfg_intent_only = {**CFG, "matrix": {**CFG["matrix"], "movement": "intent"}}
    assert compute_company(co, cts, s, cfg_intent_only, NOW)["priority"] == "A3"


def test_movimiento_congelado_es_cero():
    co = {"target_market": "Transitario PYME", "proveedor": "Excel", "pais": "España"}
    s = [Signal(str(i), "engagement", "content_download", NOW, 8, f"d{i}", "k") for i in range(4)]
    fz = {"kind": "no_interesa", "until": NOW + timedelta(days=90)}
    r = compute_company(co, [ct(str(i)) for i in range(4)], s, CFG, NOW, fz)
    assert r["movement"] == {"score": 0.0, "tier": 3}
