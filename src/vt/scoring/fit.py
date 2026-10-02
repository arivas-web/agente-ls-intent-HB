import re
import unicodedata
from difflib import SequenceMatcher


def _norm(text):
    t = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    t = re.sub(r"https?://\S+|www\.\S+", " ", t)
    t = re.sub(r"\(.*?\)", " ", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return t.strip()


def match_proveedor(value, cfg):
    """Devuelve (nombre canónico | None, método). Exacto > alias > prefijo > similitud."""
    if not value:
        return None, "vacio"
    n = _norm(value)
    canon = {_norm(k): k for k in cfg["proveedor"]}
    if n in canon:
        return canon[n], "exacto"
    alias = {_norm(k): v for k, v in cfg["proveedor_alias"].items()}
    if n in alias:
        return alias[n], "alias"
    for k, name in canon.items():            # "Solport - http://..." -> Solport
        if n.startswith(k + " "):
            return name, "prefijo"
    best, score = None, 0.0
    for k, name in canon.items():
        r = SequenceMatcher(None, n, k).ratio()
        if r > score:
            best, score = name, r
    if best and score >= cfg["proveedor_umbral_similitud"]:
        return best, "similar"
    return None, "sin_casar"


def fit_score(company, cfg):
    """company: dict con target_market, proveedor, pais (valores de HubSpot).
    Devuelve score 0-100, tier y desglose con el valor que genera cada bloque."""
    # Target market: puede haber varias categorías (separadas por ';'): cuenta la más alta.
    tms = [t.strip() for t in (company.get("target_market") or "").split(";") if t.strip()]
    tm_pts = [(cfg["target_market"].get(t, 0), t) for t in tms]
    tm_points, tm_value = max(tm_pts, default=(0, None))

    prov, how = match_proveedor(company.get("proveedor"), cfg)
    prov_points = cfg["proveedor"][prov] if prov else cfg["proveedor_otro"]

    pais = (company.get("pais") or "").strip()
    ub = cfg["ubicacion"]
    if pais in ub and pais not in ("otros_latam", "otro"):
        loc_points = ub[pais]
    elif pais in cfg["latam"]:
        loc_points = ub["otros_latam"]
    else:
        loc_points = ub["otro"]

    total = tm_points + prov_points + loc_points
    score = max(0, total) / cfg["max_points"] * 100
    tier = "A" if score >= cfg["tiers"]["A"] else "B" if score >= cfg["tiers"]["B"] else "C"
    return {
        "score": round(score, 1), "tier": tier, "raw_points": total,
        "breakdown": {
            "target_market": {"value": tm_value, "points": tm_points},
            "proveedor": {"value": company.get("proveedor"), "canonico": prov, "metodo": how, "points": prov_points},
            "ubicacion": {"value": pais or None, "points": loc_points},
        },
    }
