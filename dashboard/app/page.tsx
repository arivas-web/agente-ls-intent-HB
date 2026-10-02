import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { companiesByIds, fetchAll, inChunks, latestScores } from "@/lib/db";
import { ACCOUNTS_PER_SDR, SDRS } from "@/lib/config";
import type { Assignment, Candidate, Contact, Draft } from "@/lib/types";
import { AddManual, RowActions, ValidateButton } from "@/components/DraftControls";
import { Badge, DbError, Empty, Meters, QualityBadge, StatusBadge, short } from "@/components/ui";
import { mergeActivities, oneLiner, qualityOf } from "@/lib/activity";

export const dynamic = "force-dynamic";

export default async function SemanaSiguiente({ searchParams }: { searchParams: { draft?: string } }) {
  try {
    const sb = createClient();
    const { data: drafts, error } = await sb.from("weekly_drafts").select("*").order("week", { ascending: false }).limit(60);
    if (error) throw new Error(error.message);
    const list = (drafts ?? []) as Draft[];
    if (!list.length) return <><h1>Semana siguiente</h1><Empty>Aún no hay borradores. El motor genera uno cada semana.</Empty></>;
    const draft = list.find((d) => String(d.id) === searchParams.draft) ?? list[0];
    const readOnly = draft.status === "enviado" || draft.status === "no_enviado";

    const assignments = (await fetchAll<Assignment>((f, t) =>
      sb.from("weekly_assignments").select("*").eq("draft_id", draft.id).eq("removed", false).order("rank", { nullsFirst: false }).range(f, t)));
    const ids = assignments.map((a) => a.company_hs_id);
    const [companies, scores, cands] = await Promise.all([
      companiesByIds(sb, ids),
      latestScores(sb, ids),
      fetchAll<Candidate>((f, t) => sb.from("draft_candidates").select("*").eq("draft_id", draft.id).range(f, t)),
    ]);
    const candMap = new Map(cands.map((c) => [c.company_hs_id, c]));
    const bestIds = [...new Set(assignments.map((a) => scores.get(a.company_hs_id)?.best_contact).filter(Boolean) as string[])];
    const contacts = new Map(
      (await inChunks<Contact>(bestIds, async (chunk) => {
        const { data } = await sb.from("contacts").select("*").in("hs_id", chunk);
        return (data ?? []) as Contact[];
      })).map((c) => [c.hs_id, c])
    );

    const bySdr = (s: string) => assignments.filter((a) => a.sdr === s);
    const counts = SDRS.map((s) => ({ s, n: bySdr(s).length }));
    const warnings = counts.filter((c) => c.n !== ACCOUNTS_PER_SDR);
    const summary = counts.map((c) => `${c.s}: ${c.n} cuentas`).join(" · ");

    return (
      <>
        <h1>Semana siguiente</h1>
        <form className="row" method="get">
          <label>Borrador (semana)
            <select name="draft" defaultValue={String(draft.id)}>
              {list.map((d) => <option key={d.id} value={d.id}>{d.week} · {d.status.replace("_", " ")}</option>)}
            </select>
          </label>
          <button type="submit">Ver</button>
          <StatusBadge status={draft.status} />
          <span className="grow" />
          {draft.status === "pendiente_validar" && <ValidateButton draftId={draft.id} summary={summary} />}
        </form>
        {readOnly && <div className="notice info">Borrador {draft.status === "enviado" ? "enviado" : "no enviado"}: solo lectura.</div>}
        {warnings.length > 0 && (
          <div className="notice warn">
            Aviso: lo habitual son {ACCOUNTS_PER_SDR} cuentas por SDR. {warnings.map((w) => `${w.s} tiene ${w.n}`).join("; ")}.
          </div>
        )}

        {SDRS.map((sdr) => {
          const rows = bySdr(sdr);
          return (
            <section key={sdr}>
              <h2>{sdr} <span className="muted">({rows.length})</span></h2>
              {rows.length ? (
                <div className="acct-grid">
                  {rows.map((a) => {
                    const co = companies.get(a.company_hs_id);
                    const sc = scores.get(a.company_hs_id);
                    const cd = candMap.get(a.company_hs_id);
                    const bc = sc?.best_contact ? contacts.get(sc.best_contact) : undefined;
                    const name = co?.name ?? a.company_hs_id;
                    const prio = cd?.code ?? sc?.priority ?? null;
                    const acts = mergeActivities(sc?.breakdown?.intent?.signals, sc?.breakdown?.engagement?.signals);
                    return (
                      <article key={a.id} className={`acct ${qualityOf(prio).tone}`}>
                        <div className="acct-head">
                          <div>
                            <Link className="acct-name" href={`/cuenta/${encodeURIComponent(a.company_hs_id)}?draft=${draft.id}`}>{name}</Link>
                            <div className="acct-sub">{[co?.target_market, co?.pais].filter(Boolean).join(" · ") || co?.domain || ""}</div>
                          </div>
                          <QualityBadge priority={prio} />
                        </div>
                        <div className="acct-line">{oneLiner(acts)}</div>
                        <Meters fit={cd?.fit ?? sc?.fit} engagement={cd?.engagement ?? sc?.engagement} intent={cd?.intent ?? sc?.intent} />
                        {a.claude?.vt_why_now && <div className="ai"><div className="tag">✦ Por qué ahora</div><div>{short(a.claude.vt_why_now, 220)}</div></div>}
                        <div className="acct-foot">
                          <span className="small">{bc ? <>📞 <b>{bc.email ?? bc.hs_id}</b> <span className="muted">{bc.cargo_icp ?? ""}</span></> : <span className="muted">Sin contacto recomendado</span>}</span>
                          <span>
                            {a.is_control && <Badge>Control</Badge>}
                            {a.added_manually && <> <Badge>Manual</Badge></>}
                            {a.sdr_original && a.sdr_original !== a.sdr && <> <Badge>Antes {a.sdr_original}</Badge></>}
                          </span>
                        </div>
                        {!readOnly && <RowActions id={a.id} sdr={a.sdr} name={name} />}
                      </article>
                    );
                  })}
                </div>
              ) : <Empty>Sin cuentas.</Empty>}
            </section>
          );
        })}

        {!readOnly && <div style={{ marginTop: 20 }}><AddManual draftId={draft.id} /></div>}
      </>
    );
  } catch (e) {
    return <DbError error={e} />;
  }
}
