from datetime import timedelta
from .decay import decay, normalize
from .signals import Signal, dedupe_daily


def derive_bonuses(signals, now, cfg, url_cfg, sessions_7d=0):
    """Señales derivadas (bonus de cuenta). Se fechan en el momento de detección."""
    w = cfg["weights"]
    out = []
    recent = [s for s in signals if now - timedelta(days=cfg["multi_person_window_days"]) <= s.at <= now]
    people = {s.contact_id for s in recent if s.contact_id}
    if len(people) >= 2:
        out.append(Signal("", "intent", "multi_person_7d", now, w["multi_person_7d"],
                          f"{len(people)} contactos"))
    if sessions_7d >= cfg["sessions_7d_min"]:
        out.append(Signal("", "intent", "sessions_7d", now, w["sessions_7d"], f"{sessions_7d} sesiones"))
    # vuelta tras 90+ días sin actividad
    last7 = now - timedelta(days=7)
    if recent:
        prior = [s.at for s in signals if s.at < last7]
        if prior and (last7 - max(prior)).days >= cfg["return_after_days"]:
            out.append(Signal("", "intent", "return_after_90d", now, w["return_after_90d"]))
    # ruta de evaluación: producto/vertical Y (precios/demo/caso de éxito) en 48 h
    A, B = set(cfg["ruta_evaluacion_a"]), set(cfg["ruta_evaluacion_b"])
    web = sorted([s for s in signals if s.type == "web_visit"], key=lambda x: x.at)
    bonus_pts = next(b["puntos"] for b in url_cfg["bonus"] if b["id"] == "ruta_evaluacion")
    win = timedelta(hours=cfg["ruta_evaluacion_window_hours"])
    days_done = set()
    for a in web:
        if a.meta.get("rule_id") not in A:
            continue
        for b in web:
            if b.meta.get("rule_id") in B and abs(b.at - a.at) <= win:
                t = max(a.at, b.at)
                if t.date() not in days_done:
                    days_done.add(t.date())
                    out.append(Signal("", "intent", "ruta_evaluacion", t, bonus_pts,
                                      f"{a.meta['rule_id']}+{b.meta['rule_id']}"))
                break
    return out


def _raw(signals, now, half):
    detail, raw = [], 0.0
    for s in signals:
        d = decay(s.points, s.at, now, half)
        raw += d
        detail.append({"contact_id": s.contact_id, "type": s.type, "object": s.object_key,
                       "at": s.at.isoformat(), "raw_points": s.points, "points": round(d, 2)})
    return raw, detail


def intent_score(signals, now, cfg, url_cfg, sessions_7d=0, freeze=None):
    """freeze: None | {'kind': 'no_interesa'|'ahora_no', 'until': datetime}.
    no_interesa: intención 0 hasta 'until'. ahora_no: 0 hasta 'until'; en esa fecha entra +20."""
    sig = dedupe_daily([s for s in signals if s.kind == "intent"])
    if freeze and now < freeze["until"]:
        return {"score": 0.0, "tier": 3, "frozen": freeze["kind"], "signals": []}
    sig = sig + derive_bonuses(sig, now, cfg, url_cfg, sessions_7d)
    if freeze and freeze["kind"] == "ahora_no":
        sig.append(Signal("", "intent", "reactivation", freeze["until"], cfg["weights"]["reactivation"]))
    elif freeze and freeze["kind"] == "no_interesa":
        sig = [s for s in sig if s.at >= freeze["until"]]
    raw, detail = _raw(sig, now, cfg["half_life_days"])
    score = normalize(raw, cfg["saturation"])
    t = cfg["tiers"]
    tier = 1 if score >= t[1] else 2 if score >= t[2] else 3
    return {"score": round(score, 1), "tier": tier, "frozen": None, "signals": detail}


def intent_velocity(signals, now, cfg, url_cfg, **kw):
    """Intención hoy − intención hace 7 días (solo con señales conocidas entonces)."""
    before = now - timedelta(days=7)
    past = [s for s in signals if s.at <= before]
    return round(intent_score(signals, now, cfg, url_cfg, **kw)["score"]
                 - intent_score(past, before, cfg, url_cfg)["score"], 1)
