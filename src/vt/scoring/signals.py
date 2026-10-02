from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Signal:
    contact_id: str
    kind: str                 # "engagement" | "intent"
    type: str                 # email_click, web_visit, positive_reply...
    at: datetime
    points: float             # puntos brutos (antes del decaimiento)
    object_key: str = ""      # URL normalizada o contenido
    company_id: str = ""
    meta: dict = field(default_factory=dict)   # rule_id, producto, vertical...


def dedupe_daily(signals):
    """Misma acción sobre el mismo contenido: una vez al día como máximo."""
    seen, out = set(), []
    for s in sorted(signals, key=lambda x: x.at):
        key = (s.contact_id, s.kind, s.type, s.object_key, s.at.date())
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def apply_monthly_caps(signals, caps):
    """Topes por contacto y mes sobre puntos positivos. Devuelve señales con puntos recortados."""
    used, out = {}, []
    total_cap = caps.get("_total")
    for s in sorted(signals, key=lambda x: x.at):
        if s.points <= 0 or s.kind != "engagement":
            out.append(s)
            continue
        month = (s.contact_id, s.at.year, s.at.month)
        pts = s.points
        capkey = s.meta.get("cap_key") or s.type
        if capkey in caps:
            u = used.get((month, capkey), 0.0)
            pts = max(0.0, min(pts, caps[capkey] - u))
            used[(month, capkey)] = u + pts
        if total_cap is not None:
            u = used.get((month, "_total"), 0.0)
            pts = max(0.0, min(pts, total_cap - u))
            used[(month, "_total")] = u + pts
        if pts != s.points:
            s = Signal(**{**s.__dict__, "points": pts})
        out.append(s)
    return out
