import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { DbError, Empty, Meters, QualityBadge, show } from "@/components/ui";
import { ago } from "@/lib/activity";
import { LEVELS } from "@/lib/config";
import { FIT_TIERS, INTENT_TIERS, INTERACTION, SORTS, STATUSES, TARGETS, applyFilters, parseFilters, toQuery } from "@/lib/accounts";
import type { CompanyOverview } from "@/lib/types";

export const dynamic = "force-dynamic";
const PAGE = 25;

const d = (v: string | null) => (v ? v.slice(0, 10) : "");
const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;
function activityText(c: CompanyOverview): string {
  const parts: string[] = [];
  if (c.visits_30d) parts.push(`${plural(c.visits_30d, "visita", "visitas")} a la web`);
  if (c.email_clicks_30d) parts.push(`${plural(c.email_clicks_30d, "clic", "clics")} en correos`);
  if (c.active_contacts_30d > 1) parts.push(`${c.active_contacts_30d} personas activas`);
  return parts.length ? parts.join(" · ") : "Sin actividad";
}

export default async function Cuentas({ searchParams }: { searchParams: Record<string, string | string[] | undefined> }) {
  const f = parseFilters(searchParams);
  let body: React.ReactNode;
  try {
    const sb = createClient();
    const from = (f.page - 1) * PAGE;
    let query = sb.from("company_overview").select("*", { count: "exact" });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    query = applyFilters(query as any, f) as unknown as typeof query;
    const { data, count, error } = await query
      .order(f.sort, { ascending: f.dir === "asc", nullsFirst: false })
      .order("name", { ascending: true })
      .range(from, from + PAGE - 1);
    if (error) throw new Error(error.message);
    const rows = (data ?? []) as CompanyOverview[];
    const total = count ?? rows.length;
    const pages = Math.max(1, Math.ceil(total / PAGE));
    const href = (p: number) => `/cuentas?${toQuery(f, p)}`;
    body = rows.length ? (
      <>
        <p className="muted">{total} cuenta(s) · página {f.page} de {pages}</p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Empresa</th><th>Calidad</th><th>Perfil · Actividad · Intención</th>
                <th>Qué ha hecho (30 días)</th><th>Última acción</th><th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.hs_id}>
                  <td className="wrap"><Link href={`/cuentas/${encodeURIComponent(c.hs_id)}`}><b>{c.name ?? c.hs_id}</b></Link>
                    <div className="muted small">{[c.target_market, c.domain].filter(Boolean).join(" · ")}</div></td>
                  <td><QualityBadge priority={c.priority} /></td>
                  <td><Meters fit={c.fit} engagement={c.engagement} intent={c.intent} />
                    {c.intent_velocity !== null && Number(c.intent_velocity) > 0 && <div className="small" style={{ color: "var(--ok)", marginTop: 4 }}>▲ Intención subiendo</div>}</td>
                  <td className="small">{activityText(c)}</td>
                  <td className="small" title={d(c.last_signal_at)}>{ago(c.last_signal_at)}</td>
                  <td>{show(c.status)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="row" style={{ marginTop: 12 }}>
          {f.page > 1 && <Link href={href(f.page - 1)}>← Anterior</Link>}
          {f.page < pages && <Link href={href(f.page + 1)}>Siguiente →</Link>}
        </div>
      </>
    ) : <Empty>Ninguna cuenta cumple esos filtros.</Empty>;
  } catch (e) {
    body = <DbError error={e} />;
  }
  const sel = (name: string, value: string, opts: [string, string][], label: string) => (
    <label>{label}
      <select name={name} defaultValue={value}>
        {opts.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
      </select>
    </label>
  );
  const numIn = (name: string, value: number | undefined, label: string) => (
    <label>{label}<input name={name} type="number" min={0} step="any" defaultValue={value ?? ""} style={{ width: 90 }} /></label>
  );
  return (
    <>
      <h1>Cuentas</h1>
      <form method="get" className="card">
        <div className="row">
          <label className="grow">Buscar<input name="q" defaultValue={f.q} placeholder="Nombre o dominio…" style={{ minWidth: 200 }} /></label>
          {sel("status", f.status, [["", "Todos"], ...STATUSES.map((s): [string, string] => [s, s])], "Estado")}
          {sel("target", f.target, [["", "Todos"], ...TARGETS.map((s): [string, string] => [s, s])], "Target market")}
        </div>
        <h3>Calidad</h3>
        <div className="row">
          {sel("priority", f.priority, [["", "Todas"], ...LEVELS.map((s): [string, string] => [s, s])], "Prioridad")}
          {sel("fit_tier", f.fit_tier, [["", "Todos"], ...FIT_TIERS.map((s): [string, string] => [s, `Perfil ${s}`])], "Nivel de perfil")}
          {sel("intent_tier", f.intent_tier, [["", "Todos"], ...INTENT_TIERS.map((s): [string, string] => [s, `Intención ${s}`])], "Nivel de intención")}
          {numIn("fit_min", f.fit_min, "Perfil ≥")}{numIn("eng_min", f.eng_min, "Actividad ≥")}{numIn("int_min", f.int_min, "Intención ≥")}
          <label style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
            <input type="checkbox" name="rising" value="1" defaultChecked={f.rising} /> Intención subiendo
          </label>
        </div>
        <h3>Interacción</h3>
        <div className="row">
          {sel("inter", f.inter, Object.entries(INTERACTION), "Interacción")}
          {numIn("visits_min", f.visits_min, "Visitas web 30d ≥")}{numIn("clicks_min", f.clicks_min, "Clics email 30d ≥")}
          {numIn("contacts_min", f.contacts_min, "Contactos activos ≥")}
        </div>
        <div className="row" style={{ marginBottom: 0 }}>
          {sel("sort", f.sort, Object.entries(SORTS), "Ordenar por")}
          {sel("dir", f.dir, [["desc", "De mayor a menor"], ["asc", "De menor a mayor"]], "Orden")}
          <button className="primary" type="submit">Filtrar</button>
          <Link href="/cuentas">Quitar filtros</Link>
        </div>
      </form>
      {body}
    </>
  );
}
