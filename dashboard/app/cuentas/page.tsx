import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { DbError, Empty, d10, n0, show, Badge } from "@/components/ui";
import { LEVELS } from "@/lib/config";
import { FIT_TIERS, INTENT_TIERS, INTERACTION, SORTS, STATUSES, TARGETS, applyFilters, parseFilters, toQuery } from "@/lib/accounts";
import type { CompanyOverview } from "@/lib/types";

export const dynamic = "force-dynamic";
const PAGE = 25;

const tierTone = (t: string | null) => (t === "A" ? "ok" : t === "B" ? "warn" : "neutral");

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
                <th>Empresa</th><th>Prioridad</th><th className="num">Fit</th><th className="num">Engag.</th>
                <th className="num">Intención</th><th className="num">Vel.</th>
                <th className="num">Inter. 7d</th><th className="num">Inter. 30d</th><th className="num">Visitas 30d</th>
                <th className="num">Clics 30d</th><th className="num">Contactos activos</th><th>Última interacción</th>
                <th>Estado</th><th>Target market</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.hs_id}>
                  <td className="wrap"><Link href={`/cuentas/${encodeURIComponent(c.hs_id)}`}>{c.name ?? c.hs_id}</Link>
                    <div className="muted small">{show(c.domain)}</div></td>
                  <td>{c.priority ? <Badge tone={tierTone(c.fit_tier)}>{c.priority}</Badge> : "—"}</td>
                  <td className="num">{n0(c.fit)}</td><td className="num">{n0(c.engagement)}</td>
                  <td className="num">{n0(c.intent)}</td>
                  <td className="num">{c.intent_velocity === null ? "—" : `${c.intent_velocity > 0 ? "+" : ""}${n0(c.intent_velocity)}`}</td>
                  <td className="num">{c.signals_7d}</td><td className="num">{c.signals_30d}</td>
                  <td className="num">{c.visits_30d}</td><td className="num">{c.email_clicks_30d}</td>
                  <td className="num">{c.active_contacts_30d}</td><td>{d10(c.last_signal_at)}</td>
                  <td>{show(c.status)}</td><td className="wrap">{show(c.target_market)}</td>
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
        <h3>Puntuación</h3>
        <div className="row">
          {sel("priority", f.priority, [["", "Todas"], ...LEVELS.map((s): [string, string] => [s, s])], "Prioridad")}
          {sel("fit_tier", f.fit_tier, [["", "Todos"], ...FIT_TIERS.map((s): [string, string] => [s, `Fit ${s}`])], "Nivel de fit")}
          {sel("intent_tier", f.intent_tier, [["", "Todos"], ...INTENT_TIERS.map((s): [string, string] => [s, `Intención ${s}`])], "Nivel de intención")}
          {numIn("fit_min", f.fit_min, "Fit ≥")}{numIn("eng_min", f.eng_min, "Engagement ≥")}{numIn("int_min", f.int_min, "Intención ≥")}
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
