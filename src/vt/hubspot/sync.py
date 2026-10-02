"""Escribe las propiedades vt_ en HubSpot (empresa). DRY-RUN por defecto; real solo con --apply o VT_HUBSPOT_APPLY=true.
Escribe únicamente lo que cambió desde la última vez (hubspot_sync_state). Nunca borra nada."""
import json
import os
import sys
from ..config import load
from ..db.conn import connect
from ..assign.data import load_scores, top_interest
from .client import HubSpotClient
from .writer import ensure_properties, update_companies


def score_props(r, best_email, interest):
    return {"vt_fit_score": round(r["fit"], 1), "vt_fit_tier": r["fit_tier"],
            "vt_engagement_score": round(r["engagement"], 1), "vt_intent_score": round(r["intent"], 1),
            "vt_intent_tier": str(r["intent_tier"]), "vt_intent_velocity": round(r["velocity"], 1),
            "vt_priority": r["code"], "vt_best_contact": best_email or "",
            "vt_missing_decision_maker": bool(r["missing_decision_maker"]),
            "vt_interes_producto": interest.get("producto") or "", "vt_interes_vertical": interest.get("vertical") or ""}


def assignment_props(week, sdr, is_control, claude):
    p = {"vt_assigned_sdr": sdr, "vt_assigned_week": str(week), "vt_control_group": bool(is_control)}
    if claude:
        p.update({"vt_why_now": claude.get("vt_why_now", ""), "vt_angle": claude.get("vt_angle", ""),
                  "vt_ai_intent": claude.get("vt_ai_intent"), "vt_ai_intent_reason": claude.get("vt_ai_intent_reason", "")})
    return p


def changed(new, old):
    return {k: v for k, v in new.items() if json.dumps(old.get(k), default=str) != json.dumps(v, default=str)}


def main():
    apply = "--apply" in sys.argv or os.environ.get("VT_HUBSPOT_APPLY") == "true"
    print("MODO:", "REAL (--apply)" if apply else "DRY-RUN (no se escribe nada en HubSpot)")
    client = HubSpotClient()
    with connect() as conn:
        missing = ensure_properties(client, apply)
        print(("Propiedades creadas: " if apply else "Propiedades que se crearían: ") + (", ".join(missing) or "ninguna"))
        rows = load_scores(conn)
        emails = {r[0]: r[1] for r in conn.execute("select hs_id, email from contacts")}
        inter = {}
        for r in conn.execute("""select company_hs_id, meta->>'producto', meta->>'vertical' from signals
                                 where occurred_at > now() - interval '30 days' and type = 'web_visit'"""):
            inter.setdefault(r[0], []).append({"at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                                               "meta": {"producto": r[1], "vertical": r[2]}})
        state = {r[0]: r[1] for r in conn.execute("select company_hs_id, props from hubspot_sync_state")}
        want = {r["hs_id"]: score_props(r, emails.get(r["best_contact"]), top_interest(inter.get(r["hs_id"], [])))
                for r in rows}
        # Asignaciones del último borrador enviado/validado.
        d = conn.execute("""select id, week from weekly_drafts where status in ('enviado','validado')
                            order by week desc limit 1""").fetchone()
        if d:
            for cid, sdr, ctrl, claude in conn.execute(
                    """select company_hs_id, sdr, is_control, claude from weekly_assignments
                       where draft_id = %s and not removed""", (d[0],)):
                want.setdefault(cid, {}).update(assignment_props(d[1], sdr, ctrl, claude))
        updates = {cid: ch for cid, p in want.items() if (ch := changed(p, state.get(cid, {})))}
        print(f"Empresas con cambios: {len(updates)} de {len(want)}")

        def log(cid, prop, old, new, mode):
            conn.execute("insert into change_log(object_type,object_id,property,old_value,new_value,mode) "
                         "values ('company',%s,%s,%s,%s,%s)", (cid, prop, (state.get(cid) or {}).get(prop), str(new), mode))

        n = update_companies(client, updates, apply, log)
        if apply:
            for cid, ch in updates.items():
                conn.execute("""insert into hubspot_sync_state(company_hs_id, props) values (%s,%s)
                                on conflict (company_hs_id) do update set props = hubspot_sync_state.props || excluded.props,
                                synced_at = now()""", (cid, json.dumps(ch, default=str)))
        conn.commit()
        print(f"Escritas en HubSpot: {n}" if apply else "Dry-run: cambios registrados en change_log, nada escrito.")


if __name__ == "__main__":
    main()
