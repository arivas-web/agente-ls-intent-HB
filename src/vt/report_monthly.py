"""Informe mensual en Markdown (Claude redacta; si no hay Claude, plantilla). Propone ajustes de pesos: NUNCA los aplica."""
import json
from collections import Counter
from datetime import date, timedelta
from .claude.runner import ClaudeUnavailable, cli_runner
from .config import load
from .db.conn import connect
from .email import render
from .email.send import send
from .rates import by_dimension, compute_rates, lift, propose_weights
from .timeguard import forced, madrid_now

PROMPT = """Eres analista de ventas B2B. Redacta en español, en Markdown, el informe mensual de un sistema de priorización
de cuentas para dos SDR. Usa SOLO estos datos (JSON). Secciones: 1) Resumen, 2) Tasas puntuadas vs grupo de control (con lift y
numerador/denominador), 3) Por nivel de la matriz y por SDR, 4) Señales más presentes en las cuentas que convirtieron,
5) Propuestas de ajuste de pesos (son SOLO propuestas, no se aplican solas), 6) Limitaciones (muestras pequeñas).
Sé honesto con las muestras pequeñas: no extraigas conclusiones fuertes con menos de 10 cuentas por grupo.

DATOS:
{data}
"""


def fallback_markdown(month, d):
    L = [f"# Informe mensual {month}", "", f"Cuentas asignadas: **{d['rates']['cuentas_asignadas']}**", "",
         "## Puntuadas vs control (reunión)", f"- Puntuadas: {d['lift']['puntuada']}", f"- Control: {d['lift']['control']}",
         f"- Lift: {d['lift']['lift']}", "", "## Por SDR"]
    L += [f"- {k}: reunión {v['reunion']['num']}/{v['reunion']['den']}" for k, v in d["by_sdr"].items()]
    L += ["", "## Por nivel"] + [f"- {k}: reunión {v['reunion']['num']}/{v['reunion']['den']}" for k, v in d["by_code"].items()]
    L += ["", "## Propuestas de pesos (no aplicadas)"] + [f"- {p['signal']}: {p['action']} (ratio {p['ratio']})" for p in d["proposals"]] \
        or ["", "- Sin propuestas con muestra suficiente."]
    return "\n".join(L)


def gather(conn, start, end):
    asg = []
    for r in conn.execute("""select a.company_hs_id, a.sdr, a.is_control, d.week, c.target_market,
                                    (select priority from company_scores_daily s where s.company_hs_id = a.company_hs_id
                                     order by date desc limit 1)
                             from weekly_assignments a join weekly_drafts d on d.id = a.draft_id
                             join companies c on c.hs_id = a.company_hs_id
                             where d.status in ('validado','enviado') and not a.removed and d.week >= %s and d.week < %s""", (start, end)):
        asg.append({"company": r[0], "sdr": r[1], "group": "control" if r[2] else "puntuada", "assigned_at": r[3],
                    "target_market": r[4], "code": r[5]})
    outs = [{"company": r[0], "outcome": r[1], "at": r[2].date()} for r in conn.execute(
        "select company_hs_id, outcome, at from call_outcomes where at >= %s", (start,))]
    opps = [{"company": r[0], "status_norm": r[1], "opened_at": r[2], "closed_at": r[3]} for r in conn.execute(
        "select company_hs_id, status_norm, opened_at, closed_at from opportunities where opened_at is not null")]
    alerts = [{"company": r[0], "sent_at": r[1].date()} for r in conn.execute("select company_hs_id, sent_at from alerts_sent")]
    return asg, outs, opps, alerts


def signal_presence(conn, asg, outs, opps):
    conv = {o["company"] for o in outs if o["outcome"] == "reunion"} | {o["company"] for o in opps}
    ids = [a["company"] for a in asg]
    seen = {}
    for r in conn.execute("""select distinct company_hs_id, coalesce(meta->>'rule_id', type) from signals
                             where company_hs_id = any(%s) and points_raw > 0 and occurred_at > now() - interval '120 days'""", (ids,)):
        seen.setdefault(r[0], set()).add(r[1])
    pc, pn = Counter(), Counter()
    for cid in set(ids):
        for sig in seen.get(cid, ()):
            (pc if cid in conv else pn)[sig] += 1
    n_conv = len({c for c in ids if c in conv})
    return pc, pn, n_conv, len(set(ids)) - n_conv


def main():
    ecfg = load("email")
    n = madrid_now()
    if not forced() and not (n.day == 1 and n.hour == 7):
        print("Fuera de hora del informe mensual (día 1, 07:00 Madrid): no se hace nada.")
        return
    first = madrid_now().date().replace(day=1)
    start = (first - timedelta(days=1)).replace(day=1)
    with connect() as conn:
        asg, outs, opps, alerts = gather(conn, start, first)
        pc, pn, nc, nn = signal_presence(conn, asg, outs, opps)
        data = {"mes": str(start), "rates": compute_rates(asg, outs, opps, alerts), "lift": lift(asg, outs, opps, alerts),
                "by_sdr": by_dimension(asg, outs, opps, alerts, "sdr"), "by_code": by_dimension(asg, outs, opps, alerts, "code"),
                "by_target": by_dimension(asg, outs, opps, alerts, "target_market"),
                "signals_convertidas": dict(pc.most_common(15)), "signals_no_convertidas": dict(pn.most_common(15)),
                "proposals": propose_weights(pc, pn, nc, nn)}
        try:
            md = cli_runner(PROMPT.format(data=json.dumps(data, default=str, ensure_ascii=False)), load("claude")).strip()
            if len(md) < 200:
                raise ClaudeUnavailable("respuesta vacía")
        except ClaudeUnavailable:
            md = fallback_markdown(start, data)
        conn.execute("""insert into monthly_reports(month, markdown) values (%s,%s)
                        on conflict (month) do update set markdown = excluded.markdown""", (start, md))
        conn.execute("insert into weight_proposals(month, proposal) values (%s,%s)", (start, json.dumps(data["proposals"])))
        conn.commit()
    subj, html, text = render.monthly(start.strftime("%Y-%m"), md)
    send(subj, html, text, ecfg["recipients"]["monthly_report"])
    print("Informe mensual generado; propuestas guardadas (no se aplican).")


if __name__ == "__main__":
    main()
