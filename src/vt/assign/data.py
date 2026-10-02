"""Lectura de datos de la base para el reparto, los resúmenes y los emails."""
from collections import Counter, defaultdict


def top_interest(signals, days=30, now=None):
    """Producto y vertical más visitados. signals: [{'at': datetime, 'meta': {...}}]."""
    from datetime import datetime, timedelta, timezone
    now = now or datetime.now(timezone.utc)
    prod, vert = Counter(), Counter()
    for s in signals:
        if s["at"] >= now - timedelta(days=days):
            m = s.get("meta") or {}
            if m.get("producto"):
                prod[m["producto"]] += 1
            if m.get("vertical"):
                vert[m["vertical"]] += 1
    return {"producto": prod.most_common(1)[0][0] if prod else None,
            "vertical": vert.most_common(1)[0][0] if vert else None}


def load_scores(conn):
    """Última foto de puntuaciones unida a datos de empresa."""
    cur = conn.execute("""
        select s.company_hs_id, c.name, c.status, c.tipo_de_contacto, c.last_activity_at, c.target_market,
               c.proveedor, c.pais, s.fit, s.fit_tier, s.engagement, s.intent, s.intent_tier, s.intent_velocity,
               s.priority, s.action, s.best_contact, s.missing_decision_maker
        from company_scores_daily s join companies c on c.hs_id = s.company_hs_id
        where s.date = (select max(date) from company_scores_daily) and not c.internal""")
    keys = ("hs_id", "name", "status", "tipo_de_contacto", "last_activity_at", "target_market", "proveedor", "pais",
            "fit", "fit_tier", "engagement", "intent", "intent_tier", "velocity", "code", "action", "best_contact",
            "missing_decision_maker")
    rows = []
    for r in cur:
        d = dict(zip(keys, r))
        for k in ("fit", "engagement", "intent", "velocity"):
            d[k] = float(d[k] or 0)
        rows.append(d)
    return rows


def load_account_detail(conn, company_ids):
    """Señales recientes, contactos con persona score y oportunidades de Venzo, por empresa."""
    ids = list(company_ids)
    sig = defaultdict(list)
    for r in conn.execute("""select company_hs_id, contact_hs_id, type, object_key, occurred_at, points_raw, meta
                             from signals where company_hs_id = any(%s) and occurred_at > now() - interval '120 days'
                             and points_raw <> 0 order by occurred_at desc""", (ids,)):
        sig[r[0]].append({"contact_id": r[1], "type": r[2], "object": r[3], "at": r[4], "points": float(r[5]),
                          "meta": r[6] or {}})
    con = defaultdict(list)
    for r in conn.execute("""select c.company_hs_id, c.hs_id, c.email, c.cargo_icp, coalesce(p.persona, 0)
                             from contacts c left join contact_scores_daily p
                               on p.contact_hs_id = c.hs_id and p.date = (select max(date) from contact_scores_daily)
                             where c.company_hs_id = any(%s) and not c.excluded
                             order by coalesce(p.persona, 0) desc""", (ids,)):
        con[r[0]].append({"id": r[1], "email": r[2], "cargo": r[3], "persona": float(r[4])})
    ven = defaultdict(list)
    for r in conn.execute("""select company_hs_id, stage, status_norm, loss_reason, last_management, last_management_at
                             from opportunities where company_hs_id = any(%s) order by last_management_at desc nulls last""", (ids,)):
        ven[r[0]].append({"stage": r[1], "status": r[2], "loss_reason": r[3], "last_management": r[4],
                          "last_management_at": r[5]})
    return {i: {"signals": sig[i], "contacts": con[i], "venzo": ven[i]} for i in ids}
