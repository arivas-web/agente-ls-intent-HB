/**
 * Cálculo de tasas (funciones puras, sin acceso a datos).
 *
 * Unidad "cuenta asignada": una fila de weekly_assignments (no removed) de un borrador enviado/validado
 * cuya `week` cae en el periodo. Los eventos (llamadas, oportunidades) cuentan solo si ocurren dentro del
 * periodo y NO antes de la semana de asignación de esa cuenta.
 */
import { daysBetween, mondayOf, weeksInPeriod, type Period } from "./periods";

export interface AssignmentRow {
  company_hs_id: string;
  sdr: string;
  week: string; // YYYY-MM-DD
  is_control: boolean;
  level: string | null; // código de la matriz (A1, B2...)
  target_market: string | null;
}
export interface CallRow {
  company_hs_id: string;
  sdr: string | null;
  at: string; // ISO
  outcome: string | null;
}
export interface OppRow {
  company_hs_id: string;
  opened_at: string | null;
  closed_at: string | null;
  status_norm: string | null;
}
export interface AlertRow {
  company_hs_id: string;
  sdr: string | null;
  sent_at: string;
}

export interface Rate {
  num: number;
  den: number;
  pct: number | null; // 0-100, null si den = 0
}
export const METRICS = ["contacto", "reunion", "oportunidad", "ganada", "perdida"] as const;
export type Metric = (typeof METRICS)[number];
export type RatesBlock = Record<Metric, Rate>;

export interface RatesResult {
  cuentas: RatesBlock;
  llamadas: RatesBlock;
  diasAReunion: number | null;
  diasAOportunidad: number | null;
}

export function rate(num: number, den: number): Rate {
  return { num, den, pct: den > 0 ? (num / den) * 100 : null };
}
export function fmtPct(r: Rate | number | null): string {
  const p = r === null ? null : typeof r === "number" ? r : r.pct;
  return p === null ? "—" : `${p.toFixed(1)}%`;
}

const day = (iso: string | null) => (iso ? iso.slice(0, 10) : null);
const inPeriod = (d: string | null, p: Period) => d !== null && d >= p.from && d <= p.to;

function emptyBlock(den: number): RatesBlock {
  return { contacto: rate(0, den), reunion: rate(0, den), oportunidad: rate(0, den), ganada: rate(0, den), perdida: rate(0, den) };
}

export function computeRates(
  assignments: AssignmentRow[],
  calls: CallRow[],
  opps: OppRow[],
  period: Period
): RatesResult {
  const earliest = new Map<string, string>();
  for (const a of assignments) {
    const cur = earliest.get(a.company_hs_id);
    if (!cur || a.week < cur) earliest.set(a.company_hs_id, a.week);
  }
  const callsByCo = new Map<string, CallRow[]>();
  for (const c of calls) {
    const d = day(c.at);
    if (!inPeriod(d, period)) continue;
    const w = earliest.get(c.company_hs_id);
    if (w === undefined || d! < w) continue;
    (callsByCo.get(c.company_hs_id) ?? callsByCo.set(c.company_hs_id, []).get(c.company_hs_id)!).push(c);
  }
  const oppsByCo = new Map<string, OppRow[]>();
  for (const o of opps) {
    (oppsByCo.get(o.company_hs_id) ?? oppsByCo.set(o.company_hs_id, []).get(o.company_hs_id)!).push(o);
  }
  const isOpened = (o: OppRow, from: string) => inPeriod(day(o.opened_at), period) && day(o.opened_at)! >= from;
  const isClosed = (o: OppRow, st: string, from: string) =>
    o.status_norm === st && inPeriod(day(o.closed_at), period) && day(o.closed_at)! >= from;

  // --- sobre cuentas asignadas
  const cuentas = emptyBlock(assignments.length);
  const counts: Record<Metric, number> = { contacto: 0, reunion: 0, oportunidad: 0, ganada: 0, perdida: 0 };
  const daysMeet: number[] = [];
  const daysOpp: number[] = [];
  for (const a of assignments) {
    const cs = (callsByCo.get(a.company_hs_id) ?? []).filter((c) => day(c.at)! >= a.week);
    const os = oppsByCo.get(a.company_hs_id) ?? [];
    if (cs.some((c) => c.outcome && c.outcome !== "no_contesta")) counts.contacto++;
    const meets = cs.filter((c) => c.outcome === "reunion").map((c) => day(c.at)!).sort();
    if (meets.length) {
      counts.reunion++;
      daysMeet.push(daysBetween(a.week, meets[0]));
    }
    const opened = os.filter((o) => isOpened(o, a.week)).map((o) => day(o.opened_at)!).sort();
    if (opened.length) {
      counts.oportunidad++;
      daysOpp.push(daysBetween(a.week, opened[0]));
    }
    if (os.some((o) => isClosed(o, "ganada", a.week))) counts.ganada++;
    if (os.some((o) => isClosed(o, "perdida", a.week))) counts.perdida++;
  }
  for (const m of METRICS) cuentas[m] = rate(counts[m], assignments.length);

  // --- sobre llamadas
  const allCalls = [...callsByCo.values()].flat();
  const lc: Record<Metric, number> = { contacto: 0, reunion: 0, oportunidad: 0, ganada: 0, perdida: 0 };
  for (const c of allCalls) {
    const from = earliest.get(c.company_hs_id)!;
    const os = oppsByCo.get(c.company_hs_id) ?? [];
    if (c.outcome && c.outcome !== "no_contesta") lc.contacto++;
    if (c.outcome === "reunion") lc.reunion++;
    if (os.some((o) => isOpened(o, from))) lc.oportunidad++;
    if (os.some((o) => isClosed(o, "ganada", from))) lc.ganada++;
    if (os.some((o) => isClosed(o, "perdida", from))) lc.perdida++;
  }
  const llamadas = emptyBlock(allCalls.length);
  for (const m of METRICS) llamadas[m] = rate(lc[m], allCalls.length);

  const avg = (xs: number[]) => (xs.length ? xs.reduce((s, x) => s + x, 0) / xs.length : null);
  return { cuentas, llamadas, diasAReunion: avg(daysMeet), diasAOportunidad: avg(daysOpp) };
}

/** Alerta -> reunión: empresas con alerta en el periodo que tienen una reunión posterior a la alerta. */
export function alertToMeeting(alerts: AlertRow[], calls: CallRow[], period: Period, sdr?: string | null): Rate {
  const first = new Map<string, string>();
  for (const a of alerts) {
    if (!inPeriod(day(a.sent_at), period)) continue;
    if (sdr && a.sdr !== sdr) continue;
    const cur = first.get(a.company_hs_id);
    if (!cur || a.sent_at < cur) first.set(a.company_hs_id, a.sent_at);
  }
  let num = 0;
  for (const [co, at] of first) {
    if (calls.some((c) => c.company_hs_id === co && c.outcome === "reunion" && c.at >= at)) num++;
  }
  return rate(num, first.size);
}

export interface LiftRow {
  metric: Metric;
  puntuadas: Rate;
  control: Rate;
  lift: number | null;
}
/** Puntuadas vs control. Ignora cualquier filtro de grupo: recibe todas las asignaciones ya filtradas por lo demás. */
export function computeLift(assignments: AssignmentRow[], calls: CallRow[], opps: OppRow[], period: Period): LiftRow[] {
  const sc = computeRates(assignments.filter((a) => !a.is_control), calls, opps, period).cuentas;
  const ct = computeRates(assignments.filter((a) => a.is_control), calls, opps, period).cuentas;
  return METRICS.map((metric) => {
    const a = sc[metric].pct;
    const b = ct[metric].pct;
    return { metric, puntuadas: sc[metric], control: ct[metric], lift: a !== null && b !== null && b > 0 ? a / b : null };
  });
}

export interface BreakdownRow {
  key: string;
  asignadas: number;
  contacto: Rate;
  reunion: Rate;
  oportunidad: Rate;
}
export function breakdownBy(
  assignments: AssignmentRow[],
  calls: CallRow[],
  opps: OppRow[],
  period: Period,
  keyFn: (a: AssignmentRow) => string
): BreakdownRow[] {
  const groups = new Map<string, AssignmentRow[]>();
  for (const a of assignments) {
    const k = keyFn(a);
    (groups.get(k) ?? groups.set(k, []).get(k)!).push(a);
  }
  return [...groups.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, rows]) => {
      const r = computeRates(rows, calls, opps, period).cuentas;
      return { key, asignadas: rows.length, contacto: r.contacto, reunion: r.reunion, oportunidad: r.oportunidad };
    });
}

/** Serie semanal (cohortes por semana de asignación; eventos dentro de todo el periodo) para el mini gráfico. */
export function weeklySeries(
  assignments: AssignmentRow[],
  calls: CallRow[],
  opps: OppRow[],
  period: Period,
  metric: Metric,
  base: "cuentas" | "llamadas" = "cuentas"
): { week: string; pct: number | null }[] {
  return weeksInPeriod(period).map((w) => {
    const rows = assignments.filter((a) => mondayOf(a.week) === w);
    const r = computeRates(rows, calls, opps, period)[base][metric];
    return { week: w, pct: r.pct };
  });
}
