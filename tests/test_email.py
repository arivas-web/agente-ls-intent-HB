from vt.email import render
from vt.email.send import build_message, send

ITEM = {"rank": 1, "name": "Transitex <SL>", "code": "A1", "action": "llamar", "fit": 90.0, "engagement": 10.0,
        "intent": 70.0, "velocity": 25.0, "signals": ["Precios (hace 1 día)"], "contact": "ceo@x.es (CEO)",
        "buyer_persona": "decisor", "missing_decision_maker": True, "interest": "suite / transitarios",
        "summary": {"vt_why_now": "Vio precios.", "vt_angle": "Tiempo.", "contact_justification": "CEO."}}


def test_semanal_escapa_y_muestra_todo():
    subj, html, text = render.weekly_sdr("Emma", "2026-10-05", [ITEM, {**ITEM, "rank": 2, "summary": None, "missing_decision_maker": False}])
    assert "Emma" in subj and "Transitex &lt;SL&gt;" in html and "Falta decisor" in html
    assert "Por qué ahora" in html and "Sin resumen de Claude" in html and "A1" in text


def test_avisos():
    s, h, t = render.draft_ready("2026-10-05", 20, "https://x")
    assert "20 cuentas" in h and "https://x" in h
    assert "sin validar" in render.not_validated("2026-10-05")[0]
    assert "→ Laura" in render.alert("Acme", "Laura", "visita_precios", "d")[0]


def test_sin_credenciales_no_envia(monkeypatch):
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    assert send("a", "<p>x</p>", "x", ["a@b.es"]) is False
    m = build_message("a@b.es", ["c@d.es", "e@f.es"], "s", "<p>x</p>", "x")
    assert m["To"] == "c@d.es, e@f.es" and m.is_multipart()
