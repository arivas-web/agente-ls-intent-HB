"""Alertas (cada hora, L-V 09-18 Madrid): cuenta A que visita precios/demo, o 2+ contactos activos en 48 h.
Email corto a la SDR asignada (o a la de menor carga). No repite la misma alerta en 7 días."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from .config import load
from .db.conn import connect
from .email import render
from .email.send import send
from .hubspot.client import HubSpotClient
from .hubspot.writer import update_companies
from .timeguard import forced, in_window
import os


def detect(signals, fit_tier, cfg, now):
    """signals: [{contact_id, type, rule_id, at}] de UNA empresa. Devuelve lista de (motivo, detalle)."""
    if fit_tier not in cfg["fit_tiers"]:
        return []
    out = []
    recent = [s for s in signals if s["at"] >= now - timedelta(hours=cfg["lookback_hours"])
              and s["type"] == "web_visit" and s["rule_id"] in cfg["high_intent_rules"]]
    for rule in cfg["high_intent_rules"]:
        hit = [s for s in recent if s["rule_id"] == rule]
        if hit:
            out.append((f"visita_{rule}", f"Visita a {rule} ({len({s['contact_id'] for s in hit})} contacto/s)"))
    w = now - timedelta(hours=cfg["multi_contact_window_hours"])
    people = {s["contact_id"] for s in signals if s["at"] >= w and s["contact_id"]}
    if len(people) >= cfg["multi_contact_min"]:
        out.append(("multi_contacto_48h", f"{len(people)} contactos activos en 48 h"))
    return out


def pick_sdr(assigned, load_by_sdr, sdrs):
    """SDR que tiene la cuenta asignada; si no, la de menor carga."""
    return assigned or min(sdrs, key=lambda s: (load_by_sdr.get(s, 0), sdrs.index(s)))


def main():
    cfg, ecfg, acfg = load("alerts"), load("email"), load("assignment")
    w = cfg["window"]
    if not forced() and not in_window(w["weekdays"], w["from"], w["to"]):
        print("Fuera del horario de alertas (Madrid): no se hace nada.")
        return
    now = datetime.now(timezone.utc)
    sdrs = list(acfg["sdrs"])
    sent = 0
    with connect() as conn:
        tier = {r[0]: (r[1], r[2]) for r in conn.execute("""select s.company_hs_id, s.fit_tier, c.name from company_scores_daily s
            join companies c on c.hs_id = s.company_hs_id where s.date = (select max(date) from company_scores_daily)
            and s.fit_tier = any(%s) and not c.internal and coalesce(c.status,'') <> all(%s)""", (cfg["fit_tiers"], cfg["exclude_statuses"]))}
        sigs = defaultdict(list)
        for r in conn.execute("""select company_hs_id, contact_hs_id, type, meta->>'rule_id', occurred_at from signals
            where occurred_at > now() - interval '3 days' and points_raw > 0"""):
            if r[0] in tier:
                sigs[r[0]].append({"contact_id": r[1], "type": r[2], "rule_id": r[3], "at": r[4]})
        assigned = {r[0]: r[1] for r in conn.execute("""select company_hs_id, sdr from weekly_assignments a
            join weekly_drafts d on d.id = a.draft_id where d.status in ('validado','enviado') and not a.removed
            and d.week = (select max(week) from weekly_drafts where status in ('validado','enviado'))""")}
        load_by = defaultdict(int)
        for s in assigned.values():
            load_by[s] += 1
        recent = {(r[0], r[1]) for r in conn.execute(
            "select company_hs_id, reason from alerts_sent where sent_at > now() - make_interval(days => %s)", (cfg["dedupe_days"],))}
        updates = {}
        for cid, ss in sigs.items():
            for reason, detail in detect(ss, tier[cid][0], cfg, now):
                if (cid, reason) in recent:
                    continue
                sdr = pick_sdr(assigned.get(cid), load_by, sdrs)
                subj, html, text = render.alert(tier[cid][1] or cid, sdr, reason, detail)
                ok = send(subj, html, text, ecfg["recipients"]["alerts"])
                if not ok:      # sin credenciales o fallo de envío: NO se da por enviada (se reintentará en la siguiente hora)
                    continue
                conn.execute("insert into alerts_sent(company_hs_id, reason, sdr) values (%s,%s,%s)", (cid, reason, sdr))
                updates.setdefault(cid, {}).update({"vt_last_alert_at": now.date().isoformat(), "vt_last_alert_reason": reason})
                sent += 1
                recent.add((cid, reason))
        if updates:
            apply = os.environ.get("VT_HUBSPOT_APPLY") == "true"
            update_companies(HubSpotClient(), updates, apply, lambda cid, p, o, n, m: conn.execute(
                "insert into change_log(object_type,object_id,property,old_value,new_value,mode) values ('company',%s,%s,%s,%s,%s)",
                (cid, p, o, str(n), m)))
        conn.commit()
    print(f"Alertas nuevas: {len(updates)} cuentas | emails enviados: {sent}")


if __name__ == "__main__":
    main()
