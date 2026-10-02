"""Plantillas de email (HTML + texto). Sin dependencias externas."""
from html import escape as e

LABEL = {"llamar": "Llamar", "llamar_con_movimiento": "Llamar (hay movimiento)", "relleno_sin_intencion": "Relleno sin intención"}
CSS = "font-family:system-ui,Arial,sans-serif;font-size:14px;color:#1a1a1a"


def _wrap(title, body):
    return f'<div style="{CSS}"><h2 style="margin:0 0 12px">{e(title)}</h2>{body}</div>'


def draft_ready(week, n_accounts, url=None):
    link = f'<p><a href="{e(url)}">Abrir el dashboard y validar</a></p>' if url else ""
    return (f"Borrador semanal listo ({week})",
            _wrap("Borrador listo", f"<p>El borrador de la semana del <b>{e(str(week))}</b> tiene {n_accounts} cuentas y "
                  f"está pendiente de validar. Si el lunes a las 08:00 no está validado, no se enviará nada.</p>{link}"),
            f"Borrador de la semana {week}: {n_accounts} cuentas pendientes de validar.")


def not_validated(week):
    return (f"AVISO: semana {week} sin validar, no se ha enviado nada",
            _wrap("Semana sin validar", f"<p>A la hora del envío la semana <b>{e(str(week))}</b> no estaba validada, "
                  "así que no se ha enviado ningún email a las SDR.</p>"),
            f"La semana {week} no estaba validada: no se ha enviado nada.")


def weekly_sdr(sdr, week, items):
    """items: [{rank, name, code, action, fit, engagement, intent, velocity, signals:[str], summary:{...}|None,
    contact, buyer_persona, missing_decision_maker, interest, is_control}]"""
    rows = []
    for it in items:
        s = it.get("summary") or {}
        sig = "".join(f"<li>{e(x)}</li>" for x in it.get("signals", [])[:6]) or "<li>Sin señales recientes (cuenta de perfil).</li>"
        warn = ' <span style="color:#b42318">⚠ Falta decisor</span>' if it.get("missing_decision_maker") else ""
        rows.append(
            f'<div style="border-top:1px solid #ddd;padding:10px 0"><b>{it["rank"]}. {e(it["name"] or "")}</b> '
            f'— {e(it["code"])} · {e(LABEL.get(it["action"], it["action"] or ""))}{warn}<br>'
            f'Fit {it["fit"]:.0f} · Engagement {it["engagement"]:.0f} · Intención {it["intent"]:.0f} '
            f'(velocidad {it["velocity"]:+.0f})<br>'
            f'<b>Llamar primero a:</b> {e(it.get("contact") or "—")}'
            f'{" · persona sugerida: " + e(it["buyer_persona"]) if it.get("buyer_persona") else ""}<br>'
            f'<b>Interés:</b> {e(it.get("interest") or "—")}<ul style="margin:6px 0">{sig}</ul>'
            + (f'<b>Por qué ahora:</b> {e(s.get("vt_why_now", ""))}<br><b>Ángulo:</b> {e(s.get("vt_angle", ""))}<br>'
               f'<b>Contacto:</b> {e(s.get("contact_justification", ""))}' if s else "<i>Sin resumen de Claude.</i>")
            + "</div>")
    text = "\n".join(f'{it["rank"]}. {it["name"]} [{it["code"]}] contacto: {it.get("contact") or "-"}' for it in items)
    return (f"Tus cuentas de la semana — {sdr} ({week})", _wrap(f"{sdr}: tus {len(items)} cuentas ({week})", "".join(rows)), text)


def alert(company, sdr, reason, detail):
    return (f"ALERTA: {company} ({reason}) → {sdr}",
            _wrap("Alerta de cuenta", f"<p><b>{e(company)}</b> — {e(reason)}</p><p>{e(detail)}</p><p>Asignada a: <b>{e(sdr)}</b></p>"),
            f"{company}: {reason}. {detail}. Asignada a {sdr}.")


def notice(subject, message):
    return (subject, _wrap(subject, f"<p>{e(message)}</p>"), message)


def monthly(month, markdown):
    return (f"Informe mensual {month}", _wrap(f"Informe mensual {month}", f'<pre style="white-space:pre-wrap;{CSS}">{e(markdown)}</pre>'), markdown)
