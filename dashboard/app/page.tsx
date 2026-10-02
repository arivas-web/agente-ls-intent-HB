import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { companiesByIds, fetchAll, inChunks, latestScores } from "@/lib/db";
import { ACCOUNTS_PER_SDR, SDRS } from "@/lib/config";
import type { Assignment, Candidate, Contact, Draft } from "@/lib/types";
import { AddManual, RowActions, ValidateButton } from "@/components/DraftControls";
import { Badge, DbError, Empty, StatusBadge, n0, n1, short } from "@/components/ui";

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
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Empresa</th><th>Prioridad</th><th className="num">Fit</th><th className="num">Engag.</th><th className="num">Intención</th><th className="num">Velocidad</th>
                        <th>Contacto recomendado</th><th>Control</th><th>Motivo</th>{!readOnly && <th>Acciones</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((a) => {
                        const co = companies.get(a.company_hs_id);
                        const sc = scores.get(a.company_hs_id);
                        const cd = candMap.get(a.company_hs_id);
                        const bc = sc?.best_contact ? contacts.get(sc.best_contact) : undefined;
                        const name = co?.name ?? a.company_hs_id;
                        return (
                          <tr key={a.id}>
                            <td className="wrap">
                              <Link href={`/cuenta/${encodeURIComponent(a.company_hs_id)}?draft=${draft.id}`}>{name}</Link>
                              {a.added_manually && <> <Badge>Manual</Badge></>}
                              {a.sdr_original && a.sdr_original !== a.sdr && <> <Badge>Antes {a.sdr_original}</Badge></>}
                            </td>
                            <td><Badge tone="accent">{cd?.code ?? sc?.priority ?? "—"}</Badge></td>
                            <td className="num">{n0(cd?.fit ?? sc?.fit)}</td>
                            <td className="num">{n0(cd?.engagement ?? sc?.engagement)}</td>
                            <td className="num">{n0(cd?.intent ?? sc?.intent)}</td>
                            <td className="num">{n1(cd?.velocity ?? sc?.intent_velocity)}</td>
                            <td className="wrap">{bc ? <>{bc.email ?? bc.hs_id}<br /><span className="muted small">{bc.cargo_icp ?? "—"}</span></> : "—"}</td>
                            <td>{a.is_control ? "Sí" : "No"}</td>
                            <td className="wrap small">{short(a.claude?.vt_why_now)}</td>
                            {!readOnly && <td><RowActions id={a.id} sdr={a.sdr} name={name} /></td>}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
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
