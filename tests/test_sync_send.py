from datetime import datetime, timezone
from vt.hubspot.sync import assignment_props, changed, score_props
from vt.send_weekly import build_items, signal_lines

R = {"hs_id": "1", "name": "Acme", "fit": 88.04, "fit_tier": "A", "engagement": 12.3, "intent": 71.0, "intent_tier": 1,
     "velocity": 20.0, "code": "A1", "action": "llamar", "best_contact": "c1", "missing_decision_maker": False}


def test_props_de_puntuacion():
    p = score_props(R, "ceo@acme.es", {"producto": "suite", "vertical": None})
    assert p["vt_fit_score"] == 88.0 and p["vt_intent_tier"] == "1" and p["vt_priority"] == "A1"
    assert p["vt_interes_producto"] == "suite" and p["vt_interes_vertical"] == ""


def test_solo_cambios():
    old = {"vt_fit_score": 88.0, "vt_priority": "A2"}
    assert changed({"vt_fit_score": 88.0, "vt_priority": "A1", "vt_fit_tier": "A"}, old) == {"vt_priority": "A1", "vt_fit_tier": "A"}


def test_props_asignacion():
    p = assignment_props("2026-10-05", "Emma", True, {"vt_why_now": "x", "vt_angle": "y", "vt_ai_intent": 4, "vt_ai_intent_reason": "z"})
    assert p["vt_assigned_sdr"] == "Emma" and p["vt_control_group"] is True and p["vt_ai_intent"] == 4
    assert "vt_why_now" not in assignment_props("2026-10-05", "Emma", False, None)


def test_items_del_email():
    at = datetime(2026, 10, 1, tzinfo=timezone.utc)
    detail = {"1": {"signals": [{"at": at, "type": "web_visit", "object": "/precios/", "points": 20.0, "meta": {"producto": "suite"}}],
                    "contacts": [{"id": "c1", "email": "ceo@acme.es", "cargo": "CEO", "persona": 60}], "venzo": []}}
    asg = [{"hs_id": "1", "sdr": "Emma", "rank": 1, "is_control": False,
            "claude": {"vt_why_now": "a", "buyer_persona_suggested": {"c1": "decisor"}}}]
    it = build_items({"1": R}, asg, detail)[0]
    assert it["contact"] == "ceo@acme.es (CEO)" and it["buyer_persona"] == "decisor" and it["interest"] == "suite"
    assert signal_lines(detail["1"]["signals"]) == ["01/10 visita web /precios/ (20 pts)"]
