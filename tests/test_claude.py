import json
import pytest
from vt.claude.runner import ask_json, extract_json, summarize_account, validate_summary
from vt.config import load

CFG = load("claude")
OK = {"vt_why_now": "Visitó precios ayer.", "vt_angle": "Ahorro de tiempo. Objeción: precio.",
      "contact_justification": "Es el CEO.", "vt_ai_intent": 4, "vt_ai_intent_reason": "Dos visitas clave.",
      "buyer_persona_suggested": {"1": "decisor", "9": "otro", "2": "stopper"}}


def test_extract_json_con_texto_y_bloque():
    assert extract_json('Claro:\n```json\n{"a": {"b": 1}}\n```\nfin') == {"a": {"b": 1}}
    with pytest.raises(ValueError):
        extract_json("nada")


def test_validacion_normaliza_y_filtra():
    out = validate_summary({**OK, "vt_ai_intent": "4"}, CFG, contact_ids={"1", "2"})
    assert out["vt_ai_intent"] == 4 and out["buyer_persona_suggested"] == {"1": "decisor", "2": "stopper"}
    assert len(validate_summary({**OK, "vt_why_now": "x" * 900}, CFG)["vt_why_now"]) == CFG["max_chars"]["vt_why_now"]


@pytest.mark.parametrize("bad", [{**OK, "vt_ai_intent": 7}, {**OK, "vt_angle": ""}, {k: v for k, v in OK.items() if k != "vt_why_now"}])
def test_validacion_rechaza(bad):
    with pytest.raises(ValueError):
        validate_summary(bad, CFG)


def test_reintenta_con_json_invalido():
    llamadas = []

    def runner(p):
        llamadas.append(p)
        return "no es json" if len(llamadas) == 1 else json.dumps(OK)

    assert summarize_account("ctx", {"1", "2"}, runner, CFG)["vt_ai_intent"] == 4
    assert len(llamadas) == 2 and "no fue válida" in llamadas[1]


def test_falla_tras_reintentos():
    with pytest.raises(ValueError):
        summarize_account("ctx", set(), lambda p: "basura", CFG)
