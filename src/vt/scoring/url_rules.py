"""Reglas de visita web (config/url_scoring.yaml). Misma lógica que el script original."""
import re
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class UrlScore:
    path: str
    rule_id: str
    block: str            # intencion | engagement | ninguno
    points: float
    producto: str = ""
    vertical: str = ""
    alerta_si_fit: str = ""


def normalize(url, norm):
    path = urlparse(url.lower()).path or "/"
    if not path.endswith("/"):
        path += "/"
    path = norm["alias"].get(path, path)
    d = norm["quitar_sufijo_duplicado"]
    if re.search(d["aplicar_en"], path):
        path = re.sub(d["patron"], d["reemplazo"], path)
    return path


def score_url(url, cfg):
    p = normalize(url, cfg["normalizacion"])
    for r in cfg["reglas"]:
        m = re.search(r["patron"], p)
        if not m:
            continue
        prod = vert = ""
        if "guardar_interes_producto" in r:
            prod = m.expand(r["guardar_interes_producto"].replace("$1", "\\1"))
        if "guardar_interes_vertical" in r:
            vert = m.expand(r["guardar_interes_vertical"].replace("$1", "\\1"))
        return UrlScore(p, r["id"], r["bloque"], r["puntos"], prod, vert, r.get("alerta_si_fit", ""))
    return UrlScore(p, "sin_regla", "ninguno", 0)
