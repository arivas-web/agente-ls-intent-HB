import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { safeLike } from "@/lib/db";
import { DbError, Empty, d10, show } from "@/components/ui";
import type { Company } from "@/lib/types";

export const dynamic = "force-dynamic";
const PAGE = 25;

export default async function Cuentas({ searchParams }: { searchParams: { q?: string; p?: string } }) {
  const q = safeLike(searchParams.q ?? "");
  const page = Math.max(1, Number(searchParams.p) || 1);
  let body: React.ReactNode = <Empty>Escribe un nombre o dominio para buscar.</Empty>;
  if (q) {
    try {
      const sb = createClient();
      const from = (page - 1) * PAGE;
      const { data, count, error } = await sb.from("companies").select("*", { count: "exact" })
        .or(`name.ilike.%${q}%,domain.ilike.%${q}%`).order("name").range(from, from + PAGE - 1);
      if (error) throw new Error(error.message);
      const rows = (data ?? []) as Company[];
      const total = count ?? rows.length;
      const pages = Math.max(1, Math.ceil(total / PAGE));
      const href = (p: number) => `/cuentas?q=${encodeURIComponent(q)}&p=${p}`;
      body = rows.length ? (
        <>
          <p className="muted">{total} resultado(s) · página {page} de {pages}</p>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Empresa</th><th>Dominio</th><th>Target market</th><th>Proveedor</th><th>País</th><th>Estado</th><th>Última actividad</th></tr></thead>
              <tbody>
                {rows.map((c) => (
                  <tr key={c.hs_id}>
                    <td className="wrap"><Link href={`/cuentas/${encodeURIComponent(c.hs_id)}`}>{c.name ?? c.hs_id}</Link></td>
                    <td className="wrap">{show(c.domain)}</td><td>{show(c.target_market)}</td><td>{show(c.proveedor)}</td>
                    <td>{show(c.pais)}</td><td>{show(c.status)}</td><td>{d10(c.last_activity_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="row" style={{ marginTop: 12 }}>
            {page > 1 && <Link href={href(page - 1)}>← Anterior</Link>}
            {page < pages && <Link href={href(page + 1)}>Siguiente →</Link>}
          </div>
        </>
      ) : <Empty>Sin resultados para “{q}”.</Empty>;
    } catch (e) {
      body = <DbError error={e} />;
    }
  }
  return (
    <>
      <h1>Cuentas</h1>
      <form className="row" method="get">
        <input name="q" defaultValue={q} placeholder="Nombre o dominio…" className="grow" style={{ minWidth: 200 }} />
        <button className="primary" type="submit">Buscar</button>
      </form>
      {body}
    </>
  );
}
