import { createClient } from "@/lib/supabase/server";
import { companiesByIds, fetchAll, latestScores } from "@/lib/db";
import { LEVELS, SDRS } from "@/lib/config";
import { PERIOD_LABELS, resolvePeriod, type PeriodKey } from "@/lib/periods";
import {
  alertToMeeting, breakdownBy, computeLift, computeRates, fmtPct, weeklySeries, METRICS,
  type AlertRow, type AssignmentRow, type CallRow, type Metric, type OppRow, type Rate,
} from "@/lib/rates";
import type { Assignment, Candidate, Draft } from "@/lib/types";
import { Sparkline } from "@/components/Charts";
import { DbError, Empty } from "@/components/ui";

export const dynamic = "force-dynamic";

type SP = { periodo?: string; desde?: string; hasta?: string; sdr?: string; nivel?: string; grupo?: string; tm?: string };
const METRIC_LABEL: Record<Metric, string> = {
  contacto: "Contacto (llamada contestada)", reunion: "Reunión", oportunidad: "Oportunidad abierta", ganada: "Ganada", perdida: "Perdida",
};
const frac = (r: Rate) => `${r.num} / ${r.den}`;

export default async function Tasas({ searchParams }: { searchParams: SP }) {
  const key = (searchParams.periodo && searchParams.periodo in PERIOD_LABELS ? searchParams.periodo : "mes") as PeriodKey;
  const today = new Date().toISOString().slice(0, 10);
  const period = resolvePeriod(key, today, { from: searchParams.desde, to: searchParams.hasta });

  try {
    const sb = createClient();
    const drafts = await fetchAll<Draft>((f, t) =>
      sb.from("weekly_drafts").select("*").in("status", ["enviado", "validado"]).gte("week", period.from).lte("week", period.to).range(f, t));
    const weekOf = new Map(drafts.map((d) => [d.id, d.week]));
    const draftIds = drafts.map((d) => d.id);

    const rawAsg: Assignment[] = [];
    const cands: Candidate[] = [];
    for (let i = 0; i < draftIds.length; i += 50) {
      const chunk = draftIds.slice(i, i + 50);
      rawAsg.push(...(await fetchAll<Assignment>((f, t) => sb.from("weekly_assignments").select("*").in("draft_id", chunk).eq("removed", false).range(f, t))));
      cands.push(...(await fetchAll<Candidate>((f, t) => sb.from("draft_candidates").select("draft_id,company_hs_id,code").in("draft_id", chunk).range(f, t))));
    }
    const codeOf = new Map(cands.map((c) => [`${c.draft_id}|${c.company_hs_id}`, c.code]));
    const companies = await companiesByIds(sb, rawAsg.map((a) => a.company_hs_id));
    // Nivel: código del borrador; si falta, prioridad de la última foto.
    const needLevel = rawAsg.filter((a) => !codeOf.get(`${a.draft_id}|${a.company_hs_id}`));
    const fallback = new Map<string, string | null>();
    if (needLevel.length) {
      
      (await latestScores(sb, needLevel.map((a) => a.company_hs_id))).forEach((s, id) => fallback.set(id, s.priority));
    }
    const all: AssignmentRow[] = rawAsg.map((a) => ({
      company_hs_id: a.company_hs_id, sdr: a.sdr, week: weekOf.get(a.draft_id)!, is_control: a.is_control,
      level: codeOf.get(`${a.draft_id}|${a.company_hs_id}`) ?? fallback.get(a.company_hs_id) ?? null,
      target_market: companies.get(a.company_hs_id)?.target_market ?? null,
    }));

    const calls = await fetchAll<CallRow>((f, t) =>
      sb.from("call_outcomes").select("company_hs_id,sdr,at,outcome").gte("at", period.from).lte("at", period.to + "T23:59:59Z").range(f, t));
    const opps = await fetchAll<OppRow>((f, t) => sb.from("opportunities").select("company_hs_id,opened_at,closed_at,status_norm").range(f, t));
    const alerts = await fetchAll<AlertRow>((f, t) =>
      sb.from("alerts_sent").select("company_hs_id,sdr,sent_at").gte("sent_at", period.from).lte("sent_at", period.to + "T23:59:59Z").range(f, t));

    const tms = [...new Set(all.map((a) => a.target_market).filter(Boolean) as string[])].sort();
    const f = searchParams;
    const byOthers = (a: AssignmentRow) =>
      (!f.sdr || a.sdr === f.sdr) && (!f.nivel || a.level === f.nivel) && (!f.tm || a.target_market === f.tm);
    const noGroup = all.filter(byOthers);
    const assignments = noGroup.filter((a) => !f.grupo || (f.grupo === "control") === a.is_control);
    const callsF = f.sdr ? calls.filter((c) => c.sdr === f.sdr) : calls;

    const res = computeRates(assignments, callsF, opps, period);
    const lift = computeLift(noGroup, callsF, opps, period);
    const alert = alertToMeeting(alerts, calls, period, f.sdr);
    const series = (m: Metric, base: "cuentas" | "llamadas") => weeklySeries(assignments, callsF, opps, period, m, base).map((p) => p.pct);
    const days = (v: number | null) => (v === null ? "—" : `${v.toFixed(1)} días`);

    const breakdowns: { title: string; rows: ReturnType<typeof breakdownBy> }[] = [
      { title: "Por nivel de la matriz", rows: breakdownBy(assignments, callsF, opps, period, (a) => a.level ?? "Sin nivel") },
      { title: "Por SDR", rows: breakdownBy(assignments, callsF, opps, period, (a) => a.sdr) },
      { title: "Por target market", rows: breakdownBy(assignments, callsF, opps, period, (a) => a.target_market ?? "Sin target market") },
    ];

    return (
      <>
        <h1>Tasas</h1>
        <form className="row" method="get">
          <label>Periodo
            <select name="periodo" defaultValue={key}>{Object.entries(PERIOD_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
          </label>
          <label>Desde<input type="date" name="desde" defaultValue={key === "rango" ? period.from : ""} /></label>
          <label>Hasta<input type="date" name="hasta" defaultValue={key === "rango" ? period.to : ""} /></label>
          <label>SDR<select name="sdr" defaultValue={f.sdr ?? ""}><option value="">Todos</option>{SDRS.map((s) => <option key={s}>{s}</option>)}</select></label>
          <label>Nivel matriz<select name="nivel" defaultValue={f.nivel ?? ""}><option value="">Todos</option>{LEVELS.map((s) => <option key={s}>{s}</option>)}</select></label>
          <label>Grupo<select name="grupo" defaultValue={f.grupo ?? ""}><option value="">Todos</option><option value="puntuadas">Puntuadas</option><option value="control">Control</option></select></label>
          <label>Target market<select name="tm" defaultValue={f.tm ?? ""}><option value="">Todos</option>{tms.map((s) => <option key={s}>{s}</option>)}</select></label>
          <button className="primary" type="submit">Aplicar</button>
        </form>
        <p className="muted">Periodo: {period.from} a {period.to}. Cuentas asignadas: {assignments.length} (borradores enviados/validados de {drafts.length} semana(s)).</p>
        {key === "rango" && !f.desde && !f.hasta && <p className="muted small">Indica Desde y Hasta para un rango personalizado.</p>}

        {!assignments.length && <div className="notice info">No hay cuentas asignadas en este periodo con estos filtros; las tasas aparecen como “—”.</div>}

        <h2>Tasas del periodo</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th rowSpan={2}>Tasa</th><th colSpan={4}>Sobre cuentas asignadas</th><th colSpan={4}>Sobre llamadas</th></tr>
              <tr><th className="num">Num.</th><th className="num">Den.</th><th className="num">%</th><th>Semanal</th><th className="num">Num.</th><th className="num">Den.</th><th className="num">%</th><th>Semanal</th></tr>
            </thead>
            <tbody>
              {METRICS.map((m) => (
                <tr key={m}>
                  <td>{METRIC_LABEL[m]}</td>
                  <td className="num">{res.cuentas[m].num}</td><td className="num">{res.cuentas[m].den}</td><td className="num">{fmtPct(res.cuentas[m])}</td><td><Sparkline values={series(m, "cuentas")} /></td>
                  <td className="num">{res.llamadas[m].num}</td><td className="num">{res.llamadas[m].den}</td><td className="num">{fmtPct(res.llamadas[m])}</td><td><Sparkline values={series(m, "llamadas")} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted small">Llamadas: contestada = resultado distinto de “no contesta”. Oportunidad/ganada/perdida sobre llamadas = llamadas a empresas con esa oportunidad en el periodo. Los eventos anteriores a la semana de asignación no cuentan.</p>

        <div className="grid2">
          <div className="card">
            <h3 style={{ marginTop: 0 }}>Alerta → reunión</h3>
            <p><strong>{fmtPct(alert)}</strong> <span className="muted">({frac(alert)} empresas con alerta que tienen reunión posterior)</span></p>
          </div>
          <div className="card">
            <h3 style={{ marginTop: 0 }}>Tiempo medio desde la asignación</h3>
            <p>A reunión: <strong>{days(res.diasAReunion)}</strong><br />A oportunidad: <strong>{days(res.diasAOportunidad)}</strong></p>
          </div>
        </div>

        <h2>Puntuadas vs control</h2>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Tasa (sobre cuentas)</th><th className="num">Puntuadas</th><th className="num">Control</th><th className="num">Lift</th></tr></thead>
            <tbody>
              {lift.map((l) => (
                <tr key={l.metric}>
                  <td>{METRIC_LABEL[l.metric]}</td>
                  <td className="num">{frac(l.puntuadas)} · {fmtPct(l.puntuadas)}</td>
                  <td className="num">{frac(l.control)} · {fmtPct(l.control)}</td>
                  <td className="num">{l.lift === null ? "—" : `${l.lift.toFixed(2)}×`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted small">Lift = tasa puntuadas / tasa control. Respeta los filtros salvo el de grupo.</p>

        {breakdowns.map((b) => (
          <section key={b.title}>
            <h2>{b.title}</h2>
            {b.rows.length ? (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>{b.title.replace("Por ", "")}</th><th className="num">Asignadas</th><th className="num">Contacto</th><th className="num">Reunión</th><th className="num">Oportunidad</th></tr></thead>
                  <tbody>
                    {b.rows.map((r) => (
                      <tr key={r.key}>
                        <td>{r.key}</td><td className="num">{r.asignadas}</td>
                        <td className="num">{frac(r.contacto)} · {fmtPct(r.contacto)}</td>
                        <td className="num">{frac(r.reunion)} · {fmtPct(r.reunion)}</td>
                        <td className="num">{frac(r.oportunidad)} · {fmtPct(r.oportunidad)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <Empty>—</Empty>}
          </section>
        ))}
      </>
    );
  } catch (e) {
    return <DbError error={e} />;
  }
}
