import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { companiesByIds, fetchAll, inChunks, latestScores } from "@/lib/db";
import { LEVELS, ORIGIN_LABEL, SDRS } from "@/lib/config";
import type { Assignment, Opportunity } from "@/lib/types";
import { BarChart } from "@/components/Charts";
import { Badge, DbError, Empty, d10, show } from "@/components/ui";

export const dynamic = "force-dynamic";
const MAX_ROWS = 200;
type SP = { etapa?: string; sdr?: string; nivel?: string; origen?: string };

export default async function Oportunidades({ searchParams }: { searchParams: SP }) {
  try {
    const sb = createClient();
    const opps = await fetchAll<Opportunity>((f, t) => sb.from("opportunities").select("*").order("opened_at", { ascending: false }).range(f, t));
    if (!opps.length) return <><h1>Oportunidades</h1><Empty>Aún no hay datos de Venzo.</Empty></>;

    const ids = opps.map((o) => o.company_hs_id).filter(Boolean) as string[];
    const [companies, scores, asg] = await Promise.all([
      companiesByIds(sb, ids),
      latestScores(sb, ids),
      inChunks<Assignment & { weekly_drafts: { week: string } | null }>(ids, async (chunk) => {
        const { data } = await sb.from("weekly_assignments").select("company_hs_id,sdr,removed,weekly_drafts(week)").in("company_hs_id", chunk).eq("removed", false);
        return (data ?? []) as never;
      }),
    ]);
    const sdrOf = new Map<string, string>();
    [...asg].sort((a, b) => (a.weekly_drafts?.week ?? "").localeCompare(b.weekly_drafts?.week ?? "")).forEach((a) => sdrOf.set(a.company_hs_id, a.sdr));

    const enriched = opps.map((o) => ({
      o,
      name: companies.get(o.company_hs_id ?? "")?.name ?? o.company_hs_id ?? "—",
      sdr: sdrOf.get(o.company_hs_id ?? "") ?? null,
      nivel: scores.get(o.company_hs_id ?? "")?.priority ?? null,
    }));
    const stages = [...new Set(opps.map((o) => o.stage ?? "Sin etapa"))].sort();
    const origins = [...new Set(opps.map((o) => o.origin).filter(Boolean) as string[])].sort();
    const pass = (e: (typeof enriched)[number]) =>
      (!searchParams.sdr || e.sdr === searchParams.sdr) &&
      (!searchParams.nivel || e.nivel === searchParams.nivel) &&
      (!searchParams.origen || e.o.origin === searchParams.origen);
    const base = enriched.filter(pass);
    const filtered = base.filter((e) => !searchParams.etapa || (e.o.stage ?? "Sin etapa") === searchParams.etapa);

    const count = (keys: string[]) => {
      const m = new Map<string, number>();
      keys.forEach((k) => m.set(k, (m.get(k) ?? 0) + 1));
      return [...m.entries()].sort((a, b) => b[1] - a[1]).map(([label, value]) => ({ label, value }));
    };
    const stageData = count(base.map((e) => e.o.stage ?? "Sin etapa"));
    const lossData = count(base.filter((e) => e.o.status_norm === "perdida").map((e) => e.o.loss_reason ?? "Sin motivo"));

    return (
      <>
        <h1>Oportunidades</h1>
        <form className="row" method="get">
          <label>Etapa<select name="etapa" defaultValue={searchParams.etapa ?? ""}><option value="">Todas</option>{stages.map((s) => <option key={s}>{s}</option>)}</select></label>
          <label>SDR<select name="sdr" defaultValue={searchParams.sdr ?? ""}><option value="">Todos</option>{SDRS.map((s) => <option key={s}>{s}</option>)}</select></label>
          <label>Nivel matriz<select name="nivel" defaultValue={searchParams.nivel ?? ""}><option value="">Todos</option>{LEVELS.map((s) => <option key={s}>{s}</option>)}</select></label>
          <label>Origen<select name="origen" defaultValue={searchParams.origen ?? ""}><option value="">Todos</option>{origins.map((s) => <option key={s} value={s}>{ORIGIN_LABEL[s] ?? s}</option>)}</select></label>
          <button className="primary" type="submit">Filtrar</button>
          <Link href="/oportunidades">Limpiar</Link>
        </form>

        <div className="grid2">
          <div className="card"><h3 style={{ marginTop: 0 }}>Oportunidades por etapa</h3><BarChart data={stageData} /></div>
          <div className="card"><h3 style={{ marginTop: 0 }}>Motivos de pérdida</h3><BarChart data={lossData} empty="Sin oportunidades perdidas" /></div>
        </div>

        <h2>Lista ({filtered.length})</h2>
        {filtered.length ? (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Empresa</th><th>Etapa</th><th>Estado</th><th>Origen</th><th>SDR</th><th>Nivel</th><th>Abierta</th><th>Motivo pérdida</th><th>Última gestión</th></tr></thead>
              <tbody>
                {filtered.slice(0, MAX_ROWS).map(({ o, name, sdr, nivel }) => (
                  <tr key={o.id}>
                    <td className="wrap">{o.company_hs_id ? <Link href={`/cuentas/${encodeURIComponent(o.company_hs_id)}`}>{name}</Link> : name}</td>
                    <td>{show(o.stage)}</td>
                    <td>{o.status_norm ? <Badge tone={o.status_norm === "ganada" ? "ok" : o.status_norm === "perdida" ? "bad" : "warn"}>{o.status_norm}</Badge> : show(o.status)}</td>
                    <td>{ORIGIN_LABEL[o.origin ?? ""] ?? show(o.origin)}</td><td>{show(sdr)}</td><td>{show(nivel)}</td>
                    <td>{d10(o.opened_at)}</td><td>{show(o.loss_reason)}</td>
                    <td className="wrap">{show(o.last_management)} {o.last_management_at ? `(${d10(o.last_management_at)})` : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <Empty>Ninguna oportunidad cumple los filtros.</Empty>}
        {filtered.length > MAX_ROWS && <p className="muted small">Mostrando las {MAX_ROWS} más recientes.</p>}
      </>
    );
  } catch (e) {
    return <DbError error={e} />;
  }
}
