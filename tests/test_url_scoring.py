import pytest
from vt.scoring.url_rules import score_url, normalize

B = "https://visualtrans.com"

# (url, regla esperada, bloque, puntos) — resultados del script original (versión 1 del YAML)
CASES = [
    ("/", "home", "engagement", 1),
    ("/precios/", "precios", "intencion", 20),
    ("/precios", "precios", "intencion", 20),
    ("/PRECIOS/?utm_source=linkedin&utm_campaign=x", "precios", "intencion", 20),
    ("/solicita-tu-demo/", "demo", "intencion", 15),
    ("/contactar-2/", "contacto", "intencion", 12),
    ("/kit-digital/", "financiacion", "intencion", 10),
    ("/info-verifactu/", "normativa_con_plazo", "intencion", 10),
    ("/productos/suite/verifactu/", "normativa_con_plazo", "intencion", 10),
    ("/productos/suite/verifactu/declaracion-responsable-suite/", "declaracion_responsable", "intencion", 3),
    ("/casos-de-exito/", "caso_exito_listado", "intencion", 8),
    ("/casos-de-exito/moldtrans/", "caso_exito_detalle", "intencion", 10),
    ("/clientes/", "clientes", "intencion", 8),
    ("/deiworld/", "integraciones", "intencion", 8),
    ("/productos/", "catalogo_productos", "intencion", 5),
    ("/productos/suite/", "producto_principal", "intencion", 8),
    ("/productos/suite/modulos/integracion-web/", "producto_detalle", "intencion", 6),
    ("/productos/otros/vnotify/", "productos_otros", "intencion", 6),
    ("/transitarios-2/", "vertical", "intencion", 6),
    ("/empresa/internacional/", "empresa", "intencion", 3),
    ("/productos/suite/novedades/suite-26-07/", "novedades_producto", "engagement", 2),
    ("/recursos-incoterms-la-guia-definitiva/", "guia_recurso", "engagement", 3),
    ("/recursos/", "hub_recursos", "engagement", 2),
    ("/noticias/", "indice_noticias", "engagement", 1),
    ("/noticias/cmo-elegir-un-software-logstico/", "noticia_comparativa_compra", "intencion", 6),
    ("/noticias/visual-trans-webinar-verifactu/", "noticia_webinar_evento", "engagement", 3),
    ("/noticias/visual-trans-suite-26-07-nuevo-dossier-con-ia/", "noticia_novedad_producto", "engagement", 2),
    ("/noticias/weco-maritima-confia-en-visual-trans/", "noticia_caso_cliente", "intencion", 4),
    ("/noticias/aduana-del-guadalquivir-implanta-la-suite-visual-trans-2/", "noticia_caso_cliente", "intencion", 4),
    ("/noticias/dca-digital-como-llegar-preparado-al-5-de-octubre-de-2026/", "noticia_normativa", "engagement", 2),
    ("/noticias/la-inteligencia-artificial-en-el-sector-logstico/", "noticia_divulgativa", "engagement", 1),
    ("/noticias/feliz-navidad/", "por_defecto", "ninguno", 0),
    ("/legal/", "por_defecto", "ninguno", 0),
    ("/privacidad-2/", "por_defecto", "ninguno", 0),
    ("/form-test/", "por_defecto", "ninguno", 0),
]


@pytest.mark.parametrize("path,rule,block,points", CASES)
def test_score(url_cfg, path, rule, block, points):
    r = score_url(B + path, url_cfg)
    got = (("por_defecto" if r.rule_id == "sin_regla" else r.rule_id), r.block, r.points)
    assert got == (rule, block, points)


def test_normalizacion(url_cfg):
    n = url_cfg["normalizacion"]
    assert normalize(B + "/PRECIOS?utm=1", n) == "/precios/"
    assert normalize(B + "/contactar-2/", n) == "/contactar/"
    assert normalize(B + "/noticias/x-2/", n) == "/noticias/x/"
    assert normalize(B + "/productos/suite-2/", n) == "/productos/suite-2/"   # solo en /noticias/


def test_intereses(url_cfg):
    r = score_url(B + "/productos/vforwarding/funcionalidades/x/", url_cfg)
    assert r.producto == "vforwarding"
    assert score_url(B + "/aduanas/", url_cfg).vertical == "aduanas"
    assert score_url(B + "/precios/", url_cfg).alerta_si_fit == "A"
