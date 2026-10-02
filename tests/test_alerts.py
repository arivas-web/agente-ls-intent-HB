from datetime import datetime, timedelta, timezone
from vt.alerts import detect, pick_sdr
from vt.config import load

CFG = load("alerts")
NOW = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)


def s(c, rule, hours, typ="web_visit"):
    return {"contact_id": c, "type": typ, "rule_id": rule, "at": NOW - timedelta(hours=hours)}


def test_visita_precios_o_demo_cuenta_a():
    assert [r for r, _ in detect([s("1", "precios", 3)], "A", CFG, NOW)] == ["visita_precios"]
    assert [r for r, _ in detect([s("1", "demo", 3)], "A", CFG, NOW)] == ["visita_demo"]
    assert detect([s("1", "precios", 3)], "B", CFG, NOW) == []                 # solo cuentas A
    assert detect([s("1", "precios", 30)], "A", CFG, NOW) == []                # fuera de la ventana de 26 h
    assert detect([s("1", "empresa", 1)], "A", CFG, NOW) == []                 # regla que no alerta


def test_dos_contactos_en_48h():
    sig = [s("1", "empresa", 40), s("2", "producto_principal", 5)]
    assert [r for r, _ in detect(sig, "A", CFG, NOW)] == ["multi_contacto_48h"]
    assert detect([s("1", "empresa", 40), s("1", "empresa", 5)], "A", CFG, NOW) == []   # el mismo contacto
    assert detect([s("1", "empresa", 60), s("2", "empresa", 5)], "A", CFG, NOW) == []   # 60 h: fuera


def test_sdr_asignada_o_menor_carga():
    assert pick_sdr("Laura", {"Emma": 0, "Laura": 9}, ["Emma", "Laura"]) == "Laura"
    assert pick_sdr(None, {"Emma": 10, "Laura": 8}, ["Emma", "Laura"]) == "Laura"
    assert pick_sdr(None, {}, ["Emma", "Laura"]) == "Emma"
