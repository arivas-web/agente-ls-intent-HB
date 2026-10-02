from .decay import decay, normalize
from .signals import apply_monthly_caps, dedupe_daily


def cargo_categoria(cargo_icp, persona_cfg):
    return persona_cfg["cargo_categoria"].get(cargo_icp or "", persona_cfg["cargo_default"])


def engagement_score(signals, contacts, now, cfg, persona_cfg):
    """signals: Signal(kind='engagement'). contacts: {id: {'cargo_icp':..., 'excluded': bool}}.
    Devuelve score 0-100, desglose por señal y por contacto."""
    sigs = [s for s in signals if s.kind == "engagement"
            and not contacts.get(s.contact_id, {}).get("excluded")]
    sigs = apply_monthly_caps(dedupe_daily(sigs), cfg["caps_per_month"])
    per_contact, detail = {}, []
    for s in sigs:
        d = decay(s.points, s.at, now, cfg["half_life_days"])
        per_contact[s.contact_id] = per_contact.get(s.contact_id, 0.0) + d
        detail.append({"contact_id": s.contact_id, "type": s.type, "object": s.object_key,
                       "at": s.at.isoformat(), "raw_points": s.points, "points": round(d, 2)})
    raw, active, contacts_out = 0.0, 0, {}
    for cid, pts in per_contact.items():
        pts = max(0.0, pts)
        cat = cargo_categoria(contacts.get(cid, {}).get("cargo_icp"), persona_cfg)
        mult = cfg["cargo_multiplier"].get(cat, cfg["cargo_multiplier"]["default"])
        raw += pts * mult
        is_active = pts >= cfg["active_contact_min_points"]
        active += is_active
        contacts_out[cid] = {"points": round(pts, 2), "cargo_categoria": cat,
                             "cargo_mult": mult, "active": is_active}
    bm = cfg["breadth_multiplier"]
    breadth = bm[1] if active <= 1 else bm[2] if active == 2 else bm[3]
    score = normalize(raw * breadth, cfg["saturation"])
    return {"score": round(score, 1), "raw": round(raw, 2), "active_contacts": active,
            "breadth_multiplier": breadth, "contacts": contacts_out, "signals": detail}
