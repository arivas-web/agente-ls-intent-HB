"""Borrador semanal: reparto + textos de Claude + aviso por email. Estado inicial: pendiente_validar."""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from ..claude.context import build_context
from ..claude.runner import ClaudeUnavailable, summarize_account
from ..config import load
from ..db.conn import connect
from ..email import render
from ..email.send import send
from ..timeguard import MADRID, at_hour, DAYS, forced, madrid_now
from .build import build_draft
from .data import load_scores
from .summaries import fill_summaries


def next_monday(now=None):
    d = madrid_now(now).date()
    return d + timedelta(days=(7 - d.weekday()) % 7 or 7)


def main():
    cfg, matrix, ecfg = load("assignment"), load("priority_matrix"), load("email")
    d = cfg["draft"]
    if not forced() and not at_hour(d["weekday"], int(d["time"][:2])):
        print("Fuera de hora de borrador (Madrid): no se hace nada.")
        return
    week = next_monday()
    with connect() as conn:
        row = conn.execute("select id, status from weekly_drafts where week = %s", (week,)).fetchone()
        if row and row[1] != "pendiente_validar":
            print(f"El borrador de {week} ya está en estado {row[1]}: no se toca.")
            return
        rows = load_scores(conn)
        open_opps = {r[0] for r in conn.execute("select distinct company_hs_id from opportunities where status_norm = 'abierta'")}
        limit = datetime.now(timezone.utc) - timedelta(days=30 * cfg["inactivity_months_for_control"])
        inactive = {r["hs_id"] for r in rows if r["last_activity_at"] is None or r["last_activity_at"] < limit}
        seed = f"{cfg.get('random_seed_salt', 'vt')}-{week}"
        asg, cands = build_draft(rows, cfg, matrix, seed, open_opps, inactive)
        by_id = {r["hs_id"]: r for r in rows}
        if row:
            draft_id = row[0]
            conn.execute("delete from weekly_assignments where draft_id = %s", (draft_id,))
            conn.execute("delete from draft_candidates where draft_id = %s", (draft_id,))
        else:
            draft_id = conn.execute("insert into weekly_drafts(week) values (%s) returning id", (week,)).fetchone()[0]
        for a in asg:
            conn.execute("""insert into weekly_assignments(draft_id,company_hs_id,sdr,rank,is_control,origin,sdr_original)
                            values (%s,%s,%s,%s,%s,%s,%s)""",
                         (draft_id, a["hs_id"], a["sdr"], a["rank"], a["is_control"], a["origin"], a["sdr"]))
        for i, c in enumerate(cands, 1):
            pool = bool(c.get("is_control_pool"))
            conn.execute("""insert into draft_candidates(draft_id,company_hs_id,rank,code,fit,intent,engagement,velocity,is_control_pool)
                            values (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                         (draft_id, c["hs_id"], 1000 + i if pool else i, c["code"], c["fit"], c["intent"],
                          c["engagement"], c["velocity"], pool))
        conn.execute("insert into job_runs(job,finished_at,status,detail) values ('draft', now(), 'ok', %s)",
                     (f"week={week} cuentas={len(asg)}",))
        conn.commit()
        n_claude = 0
        if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
            n_claude = fill_summaries(conn, draft_id)[0]
    print(f"Borrador {week}: {len(asg)} cuentas ({sum(a['is_control'] for a in asg)} de control), "
          f"{sum(1 for c in cands if not c.get('is_control_pool'))} candidatos, {n_claude} resúmenes de Claude.")
    subj, html, text = render.draft_ready(week, len(asg), ecfg.get("dashboard_url"))
    send(subj, html, text, ecfg["recipients"]["draft_ready"])


if __name__ == "__main__":
    main()
