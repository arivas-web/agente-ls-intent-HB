from datetime import datetime
from vt.config import load
from vt.scoring.persona import persona_score, best_contact, missing_decision_maker
from vt.scoring.matrix import priority
from vt.scoring.signals import Signal

NOW = datetime(2026, 10, 2, 12)


def test_persona_desglose(persona_cfg, eng_cfg, int_cfg):
    c = {"cargo_icp": "CEO", "phones": ["", "600111222"], "email": "a@b.es", "linkedin_url": "https://li/x"}
    r = persona_score(c, [], NOW, persona_cfg, eng_cfg, int_cfg)
    assert r["breakdown"] == {"cargo": 40, "engagement": 0.0, "contactabilidad": 20} and r["score"] == 60


def test_persona_engagement_hasta_40(persona_cfg, eng_cfg, int_cfg):
    s = [Signal("c", "engagement", "event_visit", NOW, 100)]
    r = persona_score({"cargo_icp": "Otro"}, s, NOW, persona_cfg, eng_cfg, int_cfg)
    assert r["breakdown"]["engagement"] == 40 and r["breakdown"]["cargo"] == 0


def test_email_invalido_o_rebotado(persona_cfg, eng_cfg, int_cfg):
    f = lambda c: persona_score(c, [], NOW, persona_cfg, eng_cfg, int_cfg)["breakdown"]["contactabilidad"]
    assert f({"email": "sin-arroba"}) == 0 and f({"email": "a@b.es", "email_bounced": True}) == 0
    assert f({"email": "a@b.es"}) == 5


def test_mejor_contacto_y_falta_decisor(persona_cfg, eng_cfg, int_cfg):
    sc = {"1": persona_score({"cargo_icp": "Operativo", "phones": ["6"]}, [], NOW, persona_cfg, eng_cfg, int_cfg),
          "2": persona_score({"cargo_icp": "CEO"}, [], NOW, persona_cfg, eng_cfg, int_cfg)}
    assert best_contact(sc) == "2" and not missing_decision_maker(sc, persona_cfg)
    del sc["2"]
    assert missing_decision_maker(sc, persona_cfg)


def test_matriz():
    m = load("priority_matrix")
    assert [priority("A", t, m)[1] for t in (1, 2, 3)] == ["llamar", "llamar", "relleno_sin_intencion"]
    assert priority("B", 1, m) == ("B1", "llamar")
    assert priority("B", 2, m) == ("B2", "llamar_con_movimiento")
    assert priority("C", 1, m) == ("C1", "llamar_con_movimiento")      # perfil flojo con movimiento
    assert priority("B", 3, m)[1] == "espera" and priority("C", 3, m) == ("C3", "fuera")


def test_orden_de_reparto():
    from vt.scoring.matrix import rank
    m = load("priority_matrix")
    codes = ["A3", "C1", "B1", "A1", "B2", "A2", "C3"]
    assert sorted(codes, key=lambda c: rank(c, m)) == ["A1", "A2", "B1", "B2", "C1", "A3", "C3"]
