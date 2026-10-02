export type PeriodKey = "semana" | "semana_pasada" | "mes" | "mes_pasado" | "trimestre" | "ano" | "rango";

export const PERIOD_LABELS: Record<PeriodKey, string> = {
  semana: "Esta semana",
  semana_pasada: "Semana pasada",
  mes: "Este mes",
  mes_pasado: "Mes pasado",
  trimestre: "Trimestre",
  ano: "Año",
  rango: "Rango personalizado",
};

export interface Period {
  from: string; // YYYY-MM-DD, inclusivo
  to: string; // YYYY-MM-DD, inclusivo
}

const DAY = 86400000;

export function parseDate(s: string): Date {
  return new Date(s + "T00:00:00Z");
}
export function fmtDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}
export function addDays(s: string, n: number): string {
  return fmtDate(new Date(parseDate(s).getTime() + n * DAY));
}
/** Lunes de la semana (UTC) de la fecha dada. */
export function mondayOf(s: string): string {
  const d = parseDate(s);
  const dow = (d.getUTCDay() + 6) % 7;
  return fmtDate(new Date(d.getTime() - dow * DAY));
}
export function daysBetween(a: string, b: string): number {
  return (parseDate(b).getTime() - parseDate(a).getTime()) / DAY;
}

/** Resuelve el periodo seleccionado a un rango de fechas. `today` en YYYY-MM-DD. */
export function resolvePeriod(key: PeriodKey, today: string, custom?: { from?: string; to?: string }): Period {
  const t = parseDate(today);
  const y = t.getUTCFullYear();
  const m = t.getUTCMonth();
  const monthEnd = (yy: number, mm: number) => fmtDate(new Date(Date.UTC(yy, mm + 1, 0)));
  switch (key) {
    case "semana": {
      const from = mondayOf(today);
      return { from, to: addDays(from, 6) };
    }
    case "semana_pasada": {
      const from = addDays(mondayOf(today), -7);
      return { from, to: addDays(from, 6) };
    }
    case "mes":
      return { from: fmtDate(new Date(Date.UTC(y, m, 1))), to: monthEnd(y, m) };
    case "mes_pasado":
      return { from: fmtDate(new Date(Date.UTC(y, m - 1, 1))), to: monthEnd(y, m - 1) };
    case "trimestre": {
      const q = Math.floor(m / 3) * 3;
      return { from: fmtDate(new Date(Date.UTC(y, q, 1))), to: monthEnd(y, q + 2) };
    }
    case "ano":
      return { from: `${y}-01-01`, to: `${y}-12-31` };
    case "rango": {
      const from = custom?.from || fmtDate(new Date(Date.UTC(y, m, 1)));
      const to = custom?.to || today;
      return from <= to ? { from, to } : { from: to, to: from };
    }
  }
}

/** Lista de lunes (semanas) que intersectan el periodo. */
export function weeksInPeriod(p: Period): string[] {
  const out: string[] = [];
  for (let w = mondayOf(p.from); w <= p.to; w = addDays(w, 7)) out.push(w);
  return out;
}
