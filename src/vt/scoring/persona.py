import re
from .decay import decay, normalize
from .engagement import cargo_categoria


def persona_score(contact, signals, now, persona_cfg, eng_cfg, int_cfg):
    """contact: cargo_icp, phones[], email, email_bounced, linkedin_url.
    signals: señales de ESTE contacto (engagement + intención)."""
    cat = cargo_categoria(contact.get("cargo_icp"), persona_cfg)
    cargo_pts = persona_cfg["cargo_points"][cat]
    raw = 0.0
    for s in signals:
        half = eng_cfg["half_life_days"] if s.kind == "engagement" else int_cfg["half_life_days"]
        raw += decay(s.points, s.at, now, half)
    eng_pts = normalize(raw, persona_cfg["engagement_saturation"]) / 100 * persona_cfg["engagement_max"]
    c = persona_cfg["contactabilidad"]
    cont = 0
    if any((p or "").strip() for p in contact.get("phones", [])):
        cont += c["telefono"]
    em = contact.get("email") or ""
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", em) and not contact.get("email_bounced"):
        cont += c["email_valido"]
    if (contact.get("linkedin_url") or "").strip():
        cont += c["linkedin"]
    return {"score": round(cargo_pts + eng_pts + cont, 1), "cargo_categoria": cat,
            "breakdown": {"cargo": cargo_pts, "engagement": round(eng_pts, 1), "contactabilidad": cont}}


def best_contact(scored):
    """scored: {contact_id: persona_result}. Mayor puntuación."""
    return max(scored, key=lambda k: scored[k]["score"], default=None)


def missing_decision_maker(scored, persona_cfg):
    """Aviso 'falta decisor': ningún contacto con 30+ puntos de cargo."""
    m = persona_cfg["missing_decision_maker_min_cargo_points"]
    return not any(v["breakdown"]["cargo"] >= m for v in scored.values())
