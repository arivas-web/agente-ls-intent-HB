import re, yaml
from urllib.parse import urlparse
cfg = yaml.safe_load(open('url_scoring.yaml'))
rules = cfg['reglas']; norm = cfg['normalizacion']

def normalize(url):
    path = urlparse(url.lower()).path or '/'
    if not path.endswith('/'): path += '/'
    path = norm['alias'].get(path, path)
    d = norm['quitar_sufijo_duplicado']
    if re.search(d['aplicar_en'], path): path = re.sub(d['patron'], d['reemplazo'], path)
    return path

def score(url):
    p = normalize(url)
    for r in rules:
        m = re.search(r['patron'], p)
        if m:
            extra = ''
            for k in ('guardar_interes_producto','guardar_interes_vertical'):
                if k in r: extra = f" [{k.split('_')[-1]}={m.expand(r[k].replace('$1',chr(92)+'1'))}]"
            return p, r['id'], r['bloque'], r['puntos'], extra

B='https://visualtrans.com'
urls = """/ /precios/ /precios /PRECIOS/?utm_source=linkedin&utm_campaign=x /solicita-tu-demo/ /demo-visual-trans/
/contactar/ /contactar-2/ /ayudas-y-subvenciones/ /kit-digital/ /documento-electronico-de-control-administrativo-deca/
/autodespacho-inteligente/ /info-verifactu/ /productos/suite/verifactu/ /productos/vforwarding/verifactu/
/productos/suite/verifactu/declaracion-responsable-suite/ /productos/suite/funcionalidades/declaracion-responsable-verifactu/
/productos/suite/funcionalidades/operativa-deca-en-visual-trans-suite/ /casos-de-exito/ /casos-de-exito/moldtrans/
/clientes/ /integraciones/ /integraciones-webcargo/ /deiworld/ /productos/ /productos/suite/ /productos/vforwarding/
/productos/empuries/ /productos/virtualdua/ /productos/tariff-code/ /productos/suite/modulos/ /productos/suite/modulos/integracion-web/
/productos/vforwarding/funcionalidades/business-intelligence-vforwarding/ /productos/empuries/funcionalidades/intrastat/
/productos/otros/ /productos/otros/vnotify/ /transitarios/ /transitarios-2/ /aduanas/ /operadores/ /consignatarios/ /cargadores/ /shippers/
/empresa/ /empresa/internacional/ /about/ /productos/suite/novedades/suite-26-07/ /productos/virtualdua/novedades/
/productos/suite/novedades/historico-de-novedades/ /novedades-vf-23-2/ /destacados/ /recursos-incoterms-la-guia-definitiva/
/especiales-logistica-inteligente/ /recursos/ /biblioteca-de-recursos/ /incoterms/ /noticias/ /portal-noticias/
/noticias/cmo-elegir-un-software-logstico/ /noticias/como-encontrar-software-logistica/ /noticias/software-erp-transitario/
/noticias/valorar-software-agentes-carga/ /noticias/por-que-comprar-software-logistico-es-la-mejor-decision/
/noticias/visual-trans-webinar-verifactu/ /noticias/webinar-consignatarios/ /noticias/visual-trans-estara-en-sil-2026-con-un-encuentro-sobre-logistica-inteligente/
/noticias/visual-trans-vforwarding-261-bi-vforwarding-integrado/ /noticias/visual-trans-suite-26-07-nuevo-dossier-con-ia/
/noticias/visual-trans-virtualdua-2404-exenciones-iva-arancel-mejoradas/ /noticias/aduana-del-guadalquivir-implanta-la-suite-visual-trans/
/noticias/barcelona-cargo-opta-por-visual-trans-para-continuar-creciendo/ /noticias/weco-maritima-confia-en-visual-trans/
/noticias/aduana-del-guadalquivir-implanta-la-suite-visual-trans-2/ /noticias/dca-digital-como-llegar-preparado-al-5-de-octubre-de-2026/
/noticias/verifactu-y-factura-electrnica-para-empresas-logsticas/ /noticias/tipos-de-declaraciones-en-el-sistema-h1-pdi-dpa-dac-spa-y-sac-2025/
/noticias/la-inteligencia-artificial-en-el-sector-logstico/ /noticias/huella-de-carbono-en-logistica-del-cumplimiento-al-valor-para-el-cliente/
/noticias/feliz-navidad/ /noticias/el-puerto-de-vigo-crece-por-encima-de-la-media-nacional/ /noticias/importante-crecimiento-del-puerto-de-barcelona/
/noticias/software-logistico-espana-270-millones-inversion/ /noticias/visual-ms-crece-un-87-en-2002/ /noticias/el-grupo-davila-celebro-el-90-aniversario-de-su-fundacion/
/noticias/la-transitaria-saner-obtiene-la-certificacion-oea/ /noticias/derivados-y-activos/ /noticias/fruit-attraction-2016/
/legal/ /privacidad-2/ /confirmacion-recepcion-formulario/ /centros-de-formacion/ /avisos-de-seguridad/ /form-test/""".split()
for u in urls:
    p,i,b,pts,x = score(B+u)
    print(f"{pts:>3} {b:<10} {i:<28} {p}{x}")
