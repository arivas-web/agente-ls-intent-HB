import pytest
from vt.scoring.fit import fit_score, match_proveedor


def co(tm="Transitario PYME", prov="Excel", pais="España"):
    return {"target_market": tm, "proveedor": prov, "pais": pais}


def test_maximo_es_100(fit_cfg):
    r = fit_score(co(prov="Solución a medida"), fit_cfg)
    assert r["raw_points"] == 43 and r["score"] == 100 and r["tier"] == "A"


def test_tiers(fit_cfg):
    assert fit_score(co("Aduanas PYME", "Solport", "España"), fit_cfg)["tier"] == "B"  # 29/43=67,4
    assert fit_score(co("Aduanas PYME", "Excel", "España"), fit_cfg)["tier"] == "A"    # 33/43=76,7
    assert fit_score(co("Courier", "Excel", "Otros"), fit_cfg)["tier"] == "C"


def test_varias_categorias_cuenta_la_mas_alta(fit_cfg):
    r = fit_score(co("Courier;Transitario PYME"), fit_cfg)
    assert r["breakdown"]["target_market"] == {"value": "Transitario PYME", "points": 30}


def test_negativo_se_corta_en_cero(fit_cfg):
    r = fit_score(co("Courier", "Dependencia central", "Otros"), fit_cfg)
    assert r["raw_points"] == -10 and r["score"] == 0 and r["tier"] == "C"


@pytest.mark.parametrize("valor,canon,metodo", [
    ("Excel", "Excel", "exacto"),
    ("Esimat", "Esymat", "alias"),
    ("Click&cargo", "Click & Cargo", "exacto"),
    ("Taric", "Taric Trans", "alias"),
    ("No tienen solución", "Sin solución", "alias"),
    ("Solución propia / Dept. IT", "Solución propia", "alias"),
    ("Solport", "Solport", "exacto"),
    ("Cargowise", "Cargowise", "exacto"),
    ("Libra - Edisa", None, "sin_casar"),
    ("Sol. central extranjero", None, "sin_casar"),
    ("Desconocido", None, "sin_casar"),
    ("", None, "vacio"),
])
def test_proveedor(fit_cfg, valor, canon, metodo):
    assert match_proveedor(valor, fit_cfg) == (canon, metodo)


def test_ubicacion(fit_cfg):
    f = lambda p: fit_score(co(pais=p), fit_cfg)["breakdown"]["ubicacion"]["points"]
    assert (f("España"), f("México"), f("Portugal"), f("Chile"), f("Francia"), f("")) == (5, 2, 1, 1, 0, 0)
