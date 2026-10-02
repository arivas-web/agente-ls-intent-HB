"""Tasas del bucle de aprendizaje (puras, testeables). El dashboard calcula lo mismo en TypeScript."""
from collections import defaultdict


def rate(num, den):
    return {"num": num, "den": den, "pct": round(100 * num / den, 1) if den else None}


def _days(a, b):
    return (b - a).days


def compute_rates(assignments, outcomes, opps, alerts):
    """assignments: [{company, sdr, code, group ('puntuada'|'control'), target_market, assigned_at(date)}]
    outcomes: [{company, outcome, at}] · opps: [{company, status_norm, opened_at, closed_at}] · alerts: [{company, sent_at}]"""
    out_by, opp_by, alert_by = defaultdict(list), defaultdict(list), defaultdict(list)
    for o in outcomes:
        out_by[o["company"]].append(o)
    for o in opps:
        opp_by[o["company"]].append(o)
    for a in alerts:
        alert_by[a["company"]].append(a)
    n = len(assignments)
    contacted = meeting = opp = won = lost = 0
    d_meet, d_opp = [], []
    for a in assignments:
        outs = [o for o in out_by.get(a["company"], []) if o["at"] >= a["assigned_at"]]
        if any(o["outcome"] != "no_contesta" for o in outs):
            contacted += 1
        meets = [o for o in outs if o["outcome"] == "reunion"]
        if meets:
            meeting += 1
            d_meet.append(_days(a["assigned_at"], min(o["at"] for o in meets)))
        ops = [o for o in opp_by.get(a["company"], []) if o["opened_at"] and o["opened_at"] >= a["assigned_at"]]
        if ops:
            opp += 1
            d_opp.append(_days(a["assigned_at"], min(o["opened_at"] for o in ops)))
            won += any(o["status_norm"] == "ganada" for o in ops)
            lost += any(o["status_norm"] == "perdida" for o in ops)
    calls = [o for a in assignments for o in out_by.get(a["company"], []) if o["at"] >= a["assigned_at"]]
    ncalls = len(calls)
    alert_meet = sum(1 for c in alert_by if any(o["outcome"] == "reunion" and o["at"] >= min(x["sent_at"] for x in alert_by[c])
                                                for o in out_by.get(c, [])))
    return {
        "cuentas_asignadas": n,
        "sobre_cuentas": {"contacto": rate(contacted, n), "reunion": rate(meeting, n), "oportunidad": rate(opp, n),
                          "ganada": rate(won, n), "perdida": rate(lost, n)},
        "sobre_llamadas": {"contacto": rate(sum(o["outcome"] != "no_contesta" for o in calls), ncalls),
                           "reunion": rate(sum(o["outcome"] == "reunion" for o in calls), ncalls),
                           "oportunidad": rate(opp, ncalls), "ganada": rate(won, ncalls), "perdida": rate(lost, ncalls)},
        "alerta_a_reunion": rate(alert_meet, len(alert_by)),
        "dias_asignacion_a_reunion": round(sum(d_meet) / len(d_meet), 1) if d_meet else None,
        "dias_asignacion_a_oportunidad": round(sum(d_opp) / len(d_opp), 1) if d_opp else None,
    }


def lift(assignments, outcomes, opps, alerts, metric="reunion"):
    """Tasa de puntuadas vs control y su cociente."""
    g = {k: compute_rates([a for a in assignments if a["group"] == k], outcomes, opps, alerts)["sobre_cuentas"][metric]
         for k in ("puntuada", "control")}
    p, c = g["puntuada"]["pct"], g["control"]["pct"]
    return {"puntuada": g["puntuada"], "control": g["control"], "lift": round(p / c, 2) if p is not None and c else None}


def by_dimension(assignments, outcomes, opps, alerts, key):
    """Tasas por nivel de la matriz ('code'), por SDR ('sdr') o por target market ('target_market')."""
    groups = defaultdict(list)
    for a in assignments:
        groups[a.get(key) or "—"].append(a)
    return {k: compute_rates(v, outcomes, opps, alerts)["sobre_cuentas"] for k, v in sorted(groups.items())}


def propose_weights(presence_conv, presence_non, n_conv, n_non, min_n=5):
    """Compara la presencia de cada señal en cuentas convertidas vs no convertidas. SOLO propone; nunca aplica."""
    out = []
    for sig in sorted(set(presence_conv) | set(presence_non)):
        c, nn = presence_conv.get(sig, 0), presence_non.get(sig, 0)
        if c + nn < min_n or not n_conv or not n_non:
            continue
        pc, pn = c / n_conv, nn / n_non
        ratio = pc / pn if pn else float("inf")
        if ratio >= 2:
            out.append({"signal": sig, "action": "subir", "ratio": None if ratio == float("inf") else round(ratio, 2),
                        "convertidas": c, "no_convertidas": nn})
        elif ratio <= 0.5:
            out.append({"signal": sig, "action": "bajar", "ratio": round(ratio, 2), "convertidas": c, "no_convertidas": nn})
    return out
