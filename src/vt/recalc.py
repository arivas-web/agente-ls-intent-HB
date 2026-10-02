"""Recálculo: 4 puntuaciones + matriz -> foto diaria en Supabase. No escribe en HubSpot (eso lo hace vt.hubspot.sync)."""
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from .config import load
from .db.batch import Batch
from .db.conn import connect
from .scoring.fit import fit_score
from .scoring.engagement import engagement_score
from .scoring.intent import intent_score, intent_velocity
from .scoring.matrix import priority
from .scoring.persona import persona_score, best_contact, missing_decision_maker
from .scoring.signals import Signal

def _fmt(x):
    """Compara valores de forma estable (Decimal de la BD vs float calculado)."""
    if isinstance(x, bool) or x is None or isinstance(x, str):
        return None if x is None else str(x)
    try:
        return f"{float(x):.1f}"
    except (TypeError, ValueError):
        return str(x)


VT_PROPS = ["vt_fit_score", "vt_fit_tier", "vt_engagement_score", "vt_intent_score", "vt_intent_tier",
            "vt_intent_velocity", "vt_priority", "vt_best_contact", "vt_missing_decision_maker"]


def compute_company(co, contacts, signals, cfgs, now, freeze=None):
    """Función pura: devuelve resultado completo de una empresa (testeable sin base de datos)."""
    fit = fit_score({"target_market": co["target_market"], "proveedor": co["proveedor"], "pais": co["pais"]},
                    cfgs["fit"])
    cmap = {c["hs_id"]: c for c in contacts}
    eng = engagement_score(signals, cmap, now, cfgs["eng"], cfgs["persona"])
    wk = now - timedelta(days=7)
    sessions = sum(1 for s in signals if s.type == "session" and s.at >= wk)
    web_int = [s for s in signals if s.kind == "intent"]
    its = intent_score(web_int, now, cfgs["int"], cfgs["url"], sessions_7d=sessions, freeze=freeze)
    vel = intent_velocity(web_int, now, cfgs["int"], cfgs["url"], sessions_7d=0)
    by_contact = defaultdict(list)
    for s in signals:
        by_contact[s.contact_id].append(s)
    persona = {c["hs_id"]: persona_score(
        {"cargo_icp": c["cargo_icp"], "phones": c["phones"] or [], "email": c["email"],
         "email_bounced": c["email_bounced"], "linkedin_url": c["linkedin_url"]},
        by_contact.get(c["hs_id"], []), now, cfgs["persona"], cfgs["eng"], cfgs["int"])
        for c in contacts if not c["excluded"]}
    code, action = priority(fit["tier"], its["tier"], cfgs["matrix"])
    return {"fit": fit, "engagement": eng, "intent": its, "velocity": vel, "persona": persona,
            "priority": code, "action": action, "best_contact": best_contact(persona),
            "missing_decision_maker": missing_decision_maker(persona, cfgs["persona"]) if persona else True}


def main():
    cfgs = {k: load(v) for k, v in {"fit": "fit", "eng": "engagement", "int": "intent", "persona": "persona",
                                    "matrix": "priority_matrix", "url": "url_scoring"}.items()}
    now = datetime.now(timezone.utc)
    today = now.date()
    with connect() as conn:
        cur = conn.cursor()
        cos = [dict(zip(("hs_id", "target_market", "proveedor", "pais"), r)) for r in
               cur.execute("select hs_id,target_market,proveedor,pais from companies")]
        cts = defaultdict(list)
        for r in cur.execute("select hs_id,company_hs_id,email,cargo_icp,phones,linkedin_url,email_bounced,excluded from contacts"):
            cts[r[1]].append(dict(zip(("hs_id", "company", "email", "cargo_icp", "phones", "linkedin_url",
                                       "email_bounced", "excluded"), r)))
        sigs = defaultdict(list)
        for r in cur.execute("select company_hs_id,contact_hs_id,kind,type,object_key,occurred_at,points_raw,meta "
                             "from signals where occurred_at > now() - interval '400 days'"):
            sigs[r[0]].append(Signal(r[1], r[2], r[3], r[5], float(r[6]), r[4], r[0], r[7] or {}))
        frz = {r[0]: {"kind": r[1], "until": r[2]} for r in cur.execute("select company_hs_id,kind,until from freezes")}
        n = 0
        snap = Batch(conn, """insert into company_scores_daily(date,company_hs_id,fit,fit_tier,engagement,intent,intent_tier,
                   intent_velocity,priority,action,best_contact,missing_decision_maker,breakdown)
                   values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   on conflict (date,company_hs_id) do update set fit=excluded.fit, fit_tier=excluded.fit_tier,
                   engagement=excluded.engagement, intent=excluded.intent, intent_tier=excluded.intent_tier,
                   intent_velocity=excluded.intent_velocity, priority=excluded.priority, action=excluded.action,
                   best_contact=excluded.best_contact, missing_decision_maker=excluded.missing_decision_maker,
                   breakdown=excluded.breakdown""")
        csnap = Batch(conn, """insert into contact_scores_daily(date,contact_hs_id,company_hs_id,persona,breakdown)
                   values (%s,%s,%s,%s,%s) on conflict (date,contact_hs_id) do update
                   set persona=excluded.persona, breakdown=excluded.breakdown""")
        cache = defaultdict(int)
        for co in cos:
            res = compute_company(co, cts.get(co["hs_id"], []), sigs.get(co["hs_id"], []), cfgs, now, frz.get(co["hs_id"]))
            cache[res["priority"]] += 1
            row = (res["fit"]["score"], res["fit"]["tier"], res["engagement"]["score"], res["intent"]["score"],
                   res["intent"]["tier"], res["velocity"], res["priority"], res["best_contact"],
                   res["missing_decision_maker"])
            breakdown = {"fit": res["fit"]["breakdown"], "engagement": res["engagement"],
                         "intent": res["intent"], "action": res["action"]}
            snap.add((today, co["hs_id"], *row[:7], res["action"], row[7], row[8], json.dumps(breakdown, default=str)))
            for cid, pr in res["persona"].items():
                csnap.add((today, cid, co["hs_id"], pr["score"], json.dumps(pr["breakdown"])))
            n += 1
            if n % 500 == 0:
                snap.flush(); csnap.flush(); conn.commit()
        snap.flush(); csnap.flush(); conn.commit()
    print("empresas puntuadas:", n)
    print("distribución prioridad:", dict(sorted(cache.items())))


if __name__ == "__main__":
    main()
