"""Resúmenes de Claude para las cuentas de un borrador. Se pueden (re)generar cuando se quiera SIN regenerar el borrador:
rellena solo las asignaciones que aún no tienen resumen (p. ej. cuentas añadidas o sustituidas desde el dashboard)."""
import json
import os
import shutil
from datetime import datetime
from ..claude.context import build_context
from ..claude.runner import ClaudeUnavailable, summarize_account
from ..config import load
from ..db.conn import connect
from ..timeguard import at_hour, forced
from .data import load_account_detail, load_scores, top_interest


def claude_status():
    """Diagnóstico sin revelar secretos."""
    return {"token_configurado": bool(os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")), "cli_instalada": shutil.which("claude") is not None}


def fill_summaries(conn, draft_id, limit=None):
    """Devuelve (generados, pendientes_sin_resumen, claude_disponible)."""
    ccfg = load("claude")
    rows = {r["hs_id"]: r for r in load_scores(conn)}
    todo = [(r[0], r[1]) for r in conn.execute(
        "select id, company_hs_id from weekly_assignments where draft_id = %s and not removed and claude is null order by sdr, rank", (draft_id,))]
    if limit:
        todo = todo[:limit]
    detail = load_account_detail(conn, [c for _, c in todo])
    done, available = 0, True
    for aid, cid in todo:
        if cid not in rows:
            continue
        r, dt = rows[cid], detail[cid]
        try:
            ctx = build_context(r, [{**s, "at": s["at"].isoformat()} for s in dt["signals"]], dt["contacts"], dt["venzo"],
                                top_interest(dt["signals"]))
            summ = summarize_account(ctx, {c["id"] for c in dt["contacts"]}, cfg=ccfg)
        except ClaudeUnavailable as e:
            print("Claude no disponible:", e, claude_status())
            available = False
            break
        except ValueError as e:
            print("Resumen inválido para una cuenta:", e)
            continue
        conn.execute("update weekly_assignments set claude = %s where id = %s", (json.dumps(summ), aid))
        conn.commit()
        done += 1
    return done, len(todo) - done, available


def main():
    st = claude_status()
    print("Claude:", "token configurado" if st["token_configurado"] else "SIN token (secreto CLAUDE_CODE_OAUTH_TOKEN no configurado)",
          "| CLI", "instalada" if st["cli_instalada"] else "no instalada")
    if os.environ.get("SCHEDULED") == "1" and not forced() and not at_hour("mon", 7):
        print("Fuera de hora (lunes 07:00 Madrid): no se hace nada.")
        return
    with connect() as conn:
        d = conn.execute("""select id, week from weekly_drafts where status in ('pendiente_validar','validado')
                            order by week desc limit 1""").fetchone()
        if not d:
            print("No hay borrador pendiente ni validado.")
            return
        done, missing, ok = fill_summaries(conn, d[0])
        conn.execute("insert into job_runs(job,finished_at,status,detail) values ('summaries', now(), %s, %s)",
                     ("ok" if ok else "sin_claude", f"week={d[1]} generados={done} pendientes={missing}"))
        conn.commit()
    print(f"Resúmenes del borrador {d[1]}: generados {done}, pendientes {missing}.")


if __name__ == "__main__":
    main()
