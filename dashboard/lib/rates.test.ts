import { describe, expect, it } from "vitest";
import { alertToMeeting, breakdownBy, computeLift, computeRates, fmtPct, rate, type AssignmentRow } from "./rates";
import { resolvePeriod } from "./periods";

const P = { from: "2026-09-01", to: "2026-09-30" };
const A = (id: string, over: Partial<AssignmentRow> = {}): AssignmentRow => ({
  company_hs_id: id, sdr: "Emma", week: "2026-09-07", is_control: false, level: "A1", target_market: "Forwarder", ...over,
});

describe("rates", () => {
  it("den 0 => null y '—'", () => {
    expect(rate(0, 0).pct).toBeNull();
    expect(fmtPct(rate(0, 0))).toBe("—");
    expect(computeRates([], [], [], P).cuentas.contacto.pct).toBeNull();
  });

  it("contacto y reunión sobre cuentas y llamadas", () => {
    const as = [A("1"), A("2"), A("3"), A("4")];
    const calls = [
      { company_hs_id: "1", sdr: "Emma", at: "2026-09-08T10:00:00Z", outcome: "no_contesta" },
      { company_hs_id: "1", sdr: "Emma", at: "2026-09-09T10:00:00Z", outcome: "reunion" },
      { company_hs_id: "2", sdr: "Emma", at: "2026-09-08T10:00:00Z", outcome: "no_interesado" },
      { company_hs_id: "3", sdr: "Emma", at: "2026-09-08T10:00:00Z", outcome: "no_contesta" },
      { company_hs_id: "2", sdr: "Emma", at: "2026-08-20T10:00:00Z", outcome: "reunion" }, // fuera de periodo
    ];
    const r = computeRates(as, calls, [], P);
    expect(r.cuentas.contacto).toMatchObject({ num: 2, den: 4 });
    expect(r.cuentas.reunion).toMatchObject({ num: 1, den: 4 });
    expect(r.llamadas.contacto).toMatchObject({ num: 2, den: 4 });
    expect(r.llamadas.reunion).toMatchObject({ num: 1, den: 4 });
    expect(r.diasAReunion).toBe(2);
  });

  it("oportunidades, ganadas y perdidas", () => {
    const as = [A("1"), A("2")];
    const opps = [
      { company_hs_id: "1", opened_at: "2026-09-10", closed_at: "2026-09-20", status_norm: "ganada" },
      { company_hs_id: "2", opened_at: "2026-09-12", closed_at: null, status_norm: "abierta" },
      { company_hs_id: "2", opened_at: "2026-01-12", closed_at: "2026-09-15", status_norm: "perdida" }, // anterior a la asignación
    ];
    const r = computeRates(as, [], opps, P);
    expect(r.cuentas.oportunidad.num).toBe(2);
    expect(r.cuentas.ganada.num).toBe(1);
    expect(r.cuentas.perdida.num).toBe(1); // cierre en periodo y >= semana de asignación
    expect(r.diasAOportunidad).toBe(4);
  });

  it("lift puntuadas vs control", () => {
    const as = [A("1"), A("2"), A("3", { is_control: true }), A("4", { is_control: true })];
    const calls = [
      { company_hs_id: "1", sdr: "Emma", at: "2026-09-09T10:00:00Z", outcome: "reunion" },
      { company_hs_id: "3", sdr: "Emma", at: "2026-09-09T10:00:00Z", outcome: "reunion" },
      { company_hs_id: "4", sdr: "Emma", at: "2026-09-09T10:00:00Z", outcome: "no_contesta" },
      { company_hs_id: "2", sdr: "Emma", at: "2026-09-09T10:00:00Z", outcome: "reunion" },
    ];
    const l = computeLift(as, calls, [], P).find((x) => x.metric === "reunion")!;
    expect(l.puntuadas).toMatchObject({ num: 2, den: 2 });
    expect(l.control).toMatchObject({ num: 1, den: 2 });
    expect(l.lift).toBe(2);
    expect(computeLift([A("1")], [], [], P)[0].lift).toBeNull();
  });

  it("alerta -> reunión", () => {
    const alerts = [
      { company_hs_id: "1", sdr: "Emma", sent_at: "2026-09-10T08:00:00Z" },
      { company_hs_id: "2", sdr: "Emma", sent_at: "2026-09-11T08:00:00Z" },
    ];
    const calls = [
      { company_hs_id: "1", sdr: "Emma", at: "2026-09-12T08:00:00Z", outcome: "reunion" },
      { company_hs_id: "2", sdr: "Emma", at: "2026-09-01T08:00:00Z", outcome: "reunion" }, // anterior
    ];
    expect(alertToMeeting(alerts, calls, P)).toMatchObject({ num: 1, den: 2 });
  });

  it("desglose por nivel", () => {
    const rows = breakdownBy([A("1"), A("2", { level: "B2" })], [], [], P, (a) => a.level ?? "—");
    expect(rows.map((r) => r.key)).toEqual(["A1", "B2"]);
  });
});

describe("periods", () => {
  it("resuelve periodos", () => {
    expect(resolvePeriod("semana", "2026-10-02")).toEqual({ from: "2026-09-28", to: "2026-10-04" });
    expect(resolvePeriod("semana_pasada", "2026-10-02")).toEqual({ from: "2026-09-21", to: "2026-09-27" });
    expect(resolvePeriod("mes_pasado", "2026-01-15")).toEqual({ from: "2025-12-01", to: "2025-12-31" });
    expect(resolvePeriod("trimestre", "2026-10-02")).toEqual({ from: "2026-10-01", to: "2026-12-31" });
    expect(resolvePeriod("ano", "2026-10-02")).toEqual({ from: "2026-01-01", to: "2026-12-31" });
  });
});
