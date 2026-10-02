from vt.venzo.match import Matcher, norm_cif, norm_domain, norm_name

COS = [
    {"hs_id": "1", "cif": "B12345678", "domain": "transitex.com", "name": "Transitex, S.L."},
    {"hs_id": "2", "cif": "", "domain": "aduanasnorte.es", "name": "Aduanas Norte SA"},
    {"hs_id": "3", "cif": None, "domain": None, "name": "Logística del Sur"},
    {"hs_id": "4", "cif": "B99999999", "domain": "dup.com", "name": "Duplicada SL"},
    {"hs_id": "5", "cif": "A88888888", "domain": "dup.com", "name": "Duplicada Dos SA"},
]
M = Matcher(COS)


def test_normalizacion():
    assert norm_cif(" es-b12345678 ") == "B12345678" and norm_cif("123") == ""
    assert norm_domain("https://www.Transitex.com/contacto?x=1") == "transitex.com"
    assert norm_domain("juan@transitex.com") == "transitex.com" and norm_domain("a@gmail.com") == ""
    assert norm_name("TRANSITEX, S.L.") == "transitex" == norm_name("Transitex Sociedad Limitada")
    assert norm_name("Logística del Sur S.L.U.") == "logistica del sur"


def test_prioridad_cif_dominio_nombre():
    assert M.match({"cif": "B12345678", "domain": "otra.com", "name": "x"})["method"] == "cif"
    r = M.match({"cif": "", "domain": "info@aduanasnorte.es", "name": ""})
    assert (r["hs_id"], r["method"], r["review"]) == ("2", "dominio", False)
    r = M.match({"cif": "", "domain": "", "name": "LOGISTICA DEL SUR, S.L."})
    assert (r["hs_id"], r["method"], r["review"]) == ("3", "nombre", False)


def test_dudosas_a_revision():
    r = M.match({"cif": "", "domain": "dup.com", "name": ""})                 # dominio compartido
    assert r["review"] and r["hs_id"] is None and {c["hs_id"] for c in r["candidates"]} == {"4", "5"}
    r = M.match({"cif": "B12345678", "domain": "aduanasnorte.es", "name": ""})  # CIF dice 1, dominio dice 2
    assert r["review"] and r["method"] == "conflicto_entre_metodos"
    r = M.match({"cif": "", "domain": "", "name": "Logistica del Sur Iberica"})  # parecido, no igual
    assert r["review"] and r["method"] == "nombre_similar"


def test_sin_coincidencia():
    r = M.match({"cif": "Z00000000", "domain": "nada.com", "name": "Empresa Inexistente"})
    assert (r["hs_id"], r["method"], r["review"]) == (None, "ninguno", False)
