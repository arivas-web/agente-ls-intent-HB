"""Envío semanal (lunes 08:00 Madrid). SOLO se envía el reparto VALIDADO en el dashboard."""
from datetime import timedelta
from .assign.data import load_account_detail, load_scores, top_interest
from .config import load
from .db.conn import connect
from .email import render
from .email.send import send
from .timeguard import at_hour, forced, madrid_now

TYPE_ES = {"web_visit": "visita web", "email_click": "clic en email", "unsubscribe": "baja", "reply_detected": "respuesta"}


def signal_lines(sigs):
    return [f"{s['at'].strftime('%d/%m')} {TYPE_ES.get(s['type'], s['type'])} {s['object']} ({s['points']:.0f} pts)" for s in sigs]


def build_items(rows_by_id, assignments, detail):
    items = []
    for a in assignments:
        r, dt = rows_by_id[a["hs_id"]], detail[a["hs_id"]]
        summ = a["claude"] or None
        best = next((c for c in dt["contacts"] if c["id"] == r["best_contact"]), None)
        items.append({
            "rank": a["rank"], "name": r["name"], "code": r["code"], "action": r["action"], "fit": r["fit"],
            "engagement": r["engagement"], "intent": r["intent"], "velocity": r["velocity"],
            "signals": signal_lines(dt["signals"]), "summary": summ,
            "contact": f"{best['email']} ({best['cargo'] or 'sin cargo'})" if best else None,
            "buyer_persona": ((summ or {}).get("buyer_persona_suggested") or {}).get(r["best_contact"]),
            "missing_decision_maker": r["missing_decision_maker"], "is_control": a["is_control"],
            "interest": " / ".join(x for x in top_interest(dt["signals"]).values() if x) or None})
    return items


def main():
    cfg, ecfg = load("assignment"), load("email")
    s = cfg["send"]
    if not forced() and not at_hour(s["weekday"], int(s["time"][:2])):
        print("Fuera de hora de envío (Madrid): no se hace nada.")
        return
    d = madrid_now().date()
    week = d - timedelta(days=d.weekday())             # lunes de esta semana
    with connect() as conn:
        row = conn.execute("select id, status from weekly_drafts where week = %s", (week,)).fetchone()
        if row is None or row[1] == "pendiente_validar":
            if row:
                conn.execute("update weekly_drafts set status = 'no_enviado' where id = %s", (row[0],))
            conn.commit()
            subj, html, text = render.not_validated(week)
            send(subj, html, text, ecfg["recipients"]["notices"])
            print("Semana sin validar: no se envía nada.")
            return
        if row[1] != "validado":
            print(f"Estado {row[1]}: nada que enviar.")
            return
        rows = {r["hs_id"]: r for r in load_scores(conn)}
        asg = [dict(zip(("hs_id", "sdr", "rank", "is_control", "claude"), r)) for r in conn.execute(
            """select company_hs_id, sdr, rank, is_control, claude from weekly_assignments
               where draft_id = %s and not removed order by sdr, rank""", (row[0],))]
        detail = load_account_detail(conn, [a["hs_id"] for a in asg])
        sent = 0
        for sdr in cfg["sdrs"]:
            mine = [a for a in asg if a["sdr"] == sdr]
            if not mine:
                continue
            subj, html, text = render.weekly_sdr(sdr, week, build_items(rows, mine, detail))
            sent += bool(send(subj, html, text, ecfg["recipients"]["weekly_sdr"][sdr]))
        if sent:
            conn.execute("update weekly_drafts set status = 'enviado', sent_at = now() where id = %s", (row[0],))
        conn.execute("insert into job_runs(job,finished_at,status,detail) values ('send_weekly', now(), %s, %s)",
                     ("ok" if sent else "sin_envio", f"week={week} emails={sent}"))
        conn.commit()
    print(f"Emails enviados: {sent}")


if __name__ == "__main__":
    main()
