from datetime import datetime, timedelta
from vt.scoring.decay import decay
from vt.scoring.engagement import engagement_score
from vt.scoring.signals import Signal, dedupe_daily, apply_monthly_caps

NOW = datetime(2026, 10, 2, 12)


def sig(c, typ, pts, days_ago=0, obj="", **meta):
    return Signal(c, "engagement", typ, NOW - timedelta(days=days_ago), pts, obj, meta=meta)


def test_decay_semivida():
    assert round(decay(10, NOW - timedelta(days=30), NOW, 30), 6) == 5
    assert round(decay(10, NOW - timedelta(days=60), NOW, 30), 6) == 2.5
    assert decay(10, NOW + timedelta(days=1), NOW, 30) == 0


def test_una_vez_al_dia():
    s = [sig("a", "email_click", 3, 0, "x"), sig("a", "email_click", 3, 0, "x"), sig("a", "email_click", 3, 0, "y")]
    assert len(dedupe_daily(s)) == 2


def test_tope_mensual_clics():
    s = [sig("a", "email_click", 3, 0, f"u{i}") for i in range(10)]   # 30 pts, tope 15
    out = apply_monthly_caps(s, {"email_click": 15, "_total": 40})
    assert sum(x.points for x in out) == 15


def test_tope_total_contacto():
    s = [sig("a", "content_download", 8, 0, f"d{i}") for i in range(10)]  # 80, tope total 40
    assert sum(x.points for x in apply_monthly_caps(s, {"_total": 40})) == 40


def test_negativos_no_se_topan():
    s = [sig("a", "unsubscribe", -15, 0, "u")]
    assert apply_monthly_caps(s, {"_total": 40})[0].points == -15


def test_multiplicadores_cargo_y_amplitud(eng_cfg, persona_cfg):
    contacts = {"ceo": {"cargo_icp": "CEO"}, "op": {"cargo_icp": "Operativo"}}
    one = engagement_score([sig("ceo", "content_download", 8)], contacts, NOW, eng_cfg, persona_cfg)
    assert one["raw"] == 12 and one["breadth_multiplier"] == 1.0           # 8 × 1,5
    two = engagement_score([sig("ceo", "content_download", 8), sig("op", "content_download", 8)],
                           contacts, NOW, eng_cfg, persona_cfg)
    assert two["raw"] == 20 and two["breadth_multiplier"] == 1.3 and two["active_contacts"] == 2
    assert two["score"] == round(20 * 1.3 / 60 * 100, 1)


def test_tres_o_mas_x16(eng_cfg, persona_cfg):
    sigs = [sig(f"c{i}", "content_download", 8) for i in range(4)]
    r = engagement_score(sigs, {f"c{i}": {} for i in range(4)}, NOW, eng_cfg, persona_cfg)
    assert r["breadth_multiplier"] == 1.6


def test_excluidos_no_puntuan(eng_cfg, persona_cfg):
    r = engagement_score([sig("a", "content_download", 8)], {"a": {"excluded": True}}, NOW, eng_cfg, persona_cfg)
    assert r["score"] == 0 and r["signals"] == []


def test_tope_100(eng_cfg, persona_cfg):
    sigs = [sig(f"c{i}", "event_visit", 10) for i in range(10)]
    r = engagement_score(sigs, {f"c{i}": {"cargo_icp": "CEO"} for i in range(10)}, NOW, eng_cfg, persona_cfg)
    assert r["score"] == 100
