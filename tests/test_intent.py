from datetime import datetime, timedelta
from vt.scoring.intent import intent_score, intent_velocity
from vt.scoring.signals import Signal

NOW = datetime(2026, 10, 2, 12)


def web(c, rule, pts, hours_ago=0, days_ago=0):
    return Signal(c, "intent", "web_visit", NOW - timedelta(days=days_ago, hours=hours_ago), pts,
                  f"/{rule}/", meta={"rule_id": rule})


def test_decay_14_dias(int_cfg, url_cfg):
    r = intent_score([web("a", "precios", 20, days_ago=14)], NOW, int_cfg, url_cfg)
    assert r["signals"][0]["points"] == 10.0
    assert r["score"] == 20.0                   # 10/50*100


def test_tiers(int_cfg, url_cfg):
    hi = intent_score([Signal("a", "intent", "positive_reply", NOW, 25), web("a", "precios", 20),
                       web("a", "demo", 15)], NOW, int_cfg, url_cfg)
    assert hi["tier"] == 1
    assert intent_score([web("a", "empresa", 3)], NOW, int_cfg, url_cfg)["tier"] == 3
    assert intent_score([web("a", "precios", 20)], NOW, int_cfg, url_cfg)["tier"] == 2   # 40


def test_ruta_evaluacion(int_cfg, url_cfg):
    sigs = [web("a", "producto_principal", 8, hours_ago=30), web("a", "precios", 20, hours_ago=2)]
    r = intent_score(sigs, NOW, int_cfg, url_cfg)
    assert any(s["type"] == "ruta_evaluacion" and s["raw_points"] == 10 for s in r["signals"])
    lejos = [web("a", "producto_principal", 8, days_ago=5), web("a", "precios", 20)]
    assert not any(s["type"] == "ruta_evaluacion" for s in intent_score(lejos, NOW, int_cfg, url_cfg)["signals"])


def test_varias_personas_7d(int_cfg, url_cfg):
    r = intent_score([web("a", "empresa", 3), web("b", "empresa", 3, days_ago=2)], NOW, int_cfg, url_cfg)
    assert any(s["type"] == "multi_person_7d" for s in r["signals"])


def test_sesiones_7d(int_cfg, url_cfg):
    r = intent_score([web("a", "empresa", 3)], NOW, int_cfg, url_cfg, sessions_7d=3)
    assert any(s["type"] == "sessions_7d" for s in r["signals"])


def test_vuelta_tras_90_dias(int_cfg, url_cfg):
    sigs = [web("a", "empresa", 3, days_ago=200), web("a", "empresa", 3)]
    assert any(s["type"] == "return_after_90d" for s in intent_score(sigs, NOW, int_cfg, url_cfg)["signals"])
    sigs = [web("a", "empresa", 3, days_ago=40), web("a", "empresa", 3)]
    assert not any(s["type"] == "return_after_90d" for s in intent_score(sigs, NOW, int_cfg, url_cfg)["signals"])


def test_no_interesa_congela(int_cfg, url_cfg):
    fz = {"kind": "no_interesa", "until": NOW + timedelta(days=90)}
    r = intent_score([web("a", "precios", 20)], NOW, int_cfg, url_cfg, freeze=fz)
    assert r["score"] == 0 and r["frozen"] == "no_interesa"


def test_ahora_no_reactiva_con_20(int_cfg, url_cfg):
    fz = {"kind": "ahora_no", "until": NOW + timedelta(days=30)}
    assert intent_score([], NOW, int_cfg, url_cfg, freeze=fz)["score"] == 0
    r = intent_score([], NOW + timedelta(days=30), int_cfg, url_cfg, freeze=fz)
    assert r["score"] == 40.0                   # +20 sobre saturación 50


def test_velocidad(int_cfg, url_cfg):
    sigs = [web("a", "precios", 20, days_ago=10), web("a", "demo", 15, days_ago=1)]
    v = intent_velocity(sigs, NOW, int_cfg, url_cfg)
    assert v > 0
