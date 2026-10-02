"""Convierte el historial de propiedades de un contacto en señales. Puro (sin red) y testeable."""
from datetime import datetime, timezone
from ..scoring.signals import Signal
from ..scoring.url_rules import score_url


def parse_ts(v):
    v = str(v)
    if v.isdigit():                                   # epoch ms
        return datetime.fromtimestamp(int(v) / 1000, tz=timezone.utc)
    return datetime.fromisoformat(v.replace("Z", "+00:00"))


def _versions(ph, prop):
    """Versiones con fecha en orden cronológico."""
    out = [(parse_ts(v["timestamp"]), v.get("value")) for v in (ph.get(prop) or []) if v.get("timestamp")]
    return sorted(out, key=lambda x: x[0])


def _increments(vers):
    """Cada aumento de un contador = N eventos fechados en la versión que lo produjo."""
    prev, out = None, []
    for ts, val in vers:
        try:
            n = int(float(val))
        except (TypeError, ValueError):
            continue
        if prev is not None and n > prev:
            out.append((ts, n - prev))
        prev = n
    return out


def signals_from_history(contact_id, company_id, ph, url_cfg, eng_cfg, props, reply_points=0):
    """ph: propertiesWithHistory del contacto. props: nombres de config/hubspot_properties.yaml."""
    sigs = []
    # Visitas web: cada cambio de última URL = una visita.
    for ts, url in _versions(ph, props["last_url"]):
        if not url:
            continue
        u = score_url(url, url_cfg)
        if u.block == "ninguno":
            continue
        meta = {"rule_id": u.rule_id, "producto": u.producto, "vertical": u.vertical}
        if u.block == "engagement" and (u.rule_id.startswith("noticia_") or u.rule_id == "indice_noticias"):
            meta["cap_key"] = "web_noticias"
        sigs.append(Signal(contact_id, "intent" if u.block == "intencion" else "engagement",
                           "web_visit", ts, u.points, u.path, company_id, meta))
    # Clics de email: cada versión de "fecha del último clic" ES un clic con su fecha (el contador acumulado
    # perdía el primer clic de cada contacto, que no tiene versión anterior con la que comparar).
    clicks = _versions(ph, props["email_last_click"]) if props.get("email_last_click") else []
    for _, val in clicks:
        try:
            at = parse_ts(val)
        except (TypeError, ValueError):
            continue
        sigs.append(Signal(contact_id, "engagement", "email_click", at,
                           eng_cfg["weights"]["email_click"], "marketing_email", company_id, {"clicks": 1}))
    if not clicks:
        for ts, n in _increments(_versions(ph, props["email_clicks"])):
            sigs.append(Signal(contact_id, "engagement", "email_click", ts,
                               eng_cfg["weights"]["email_click"], "marketing_email", company_id, {"clicks": n}))
    # Baja de suscripción.
    for ts, val in _versions(ph, props["email_optout"]):
        if str(val).lower() == "true":
            sigs.append(Signal(contact_id, "engagement", "unsubscribe", ts,
                               eng_cfg["weights"]["unsubscribe"], "optout", company_id))
            break
    # Respuesta de email detectada: puntos base (config intent.weights.reply_detected). No sabemos si es positiva.
    for ts, val in _versions(ph, props["email_last_replied"]):
        if val:
            sigs.append(Signal(contact_id, "intent", "reply_detected", ts, reply_points, str(val), company_id))
    # Sesiones web: cada versión de "fecha de la última sesión" es una sesión (bonus de 3+ sesiones en 7 días).
    visits = _versions(ph, props["last_visit"]) if props.get("last_visit") else []
    for _, val in visits:
        try:
            at = parse_ts(val)
        except (TypeError, ValueError):
            continue
        sigs.append(Signal(contact_id, "engagement", "session", at, 0, at.isoformat(), company_id))
    if not visits:
        for ts, n in _increments(_versions(ph, props["visits"])):
            for i in range(n):
                sigs.append(Signal(contact_id, "engagement", "session", ts, 0, f"{ts.isoformat()}#{i}", company_id))
    return sigs
