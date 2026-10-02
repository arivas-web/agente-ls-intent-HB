import { describe, expect, it } from "vitest";
import { applyFilters, parseFilters, toQuery, type Q } from "./accounts";

function recorder() {
  const calls: string[] = [];
  const q: Q = {
    or: (f) => (calls.push(`or ${f}`), q), eq: (c, v) => (calls.push(`eq ${c}=${v}`), q),
    gte: (c, v) => (calls.push(`gte ${c}>=${v}`), q), gt: (c, v) => (calls.push(`gt ${c}>${v}`), q),
  };
  return { q, calls };
}

describe("filtros de cuentas", () => {
  it("valores por defecto", () => {
    const f = parseFilters({});
    expect(f).toMatchObject({ sort: "intent", dir: "desc", page: 1, rising: false, inter: "" });
    const { q, calls } = recorder();
    applyFilters(q, f);
    expect(calls).toEqual([]);   // por defecto se muestran todos los estados, también Account
  });
  it("puntuación e interacción", () => {
    const f = parseFilters({ fit_tier: "A", intent_min: "x", int_min: "20", rising: "1", inter: "7d", visits_min: "2", contacts_min: "2", priority: "A1" });
    const { q, calls } = recorder();
    applyFilters(q, f);
    expect(calls).toEqual(["eq fit_tier=A", "eq priority=A1", "gte intent>=20", "gt intent_velocity>0", "gte signals_7d>=1", "gte visits_30d>=2", "gte active_contacts_30d>=2"]);
  });
  it("sin interacción y entradas inválidas se ignoran", () => {
    const f = parseFilters({ inter: "none", fit_tier: "Z", sort: "drop table", priority: "A9", fit_min: "abc", q: "a%,b(c)" });
    expect(f.fit_tier).toBe("");
    expect(f.sort).toBe("intent");
    const { q, calls } = recorder();
    applyFilters(q, f);
    expect(calls).toEqual(["or name.ilike.%a b c%,domain.ilike.%a b c%", "eq signals_30d=0"]);
  });
  it("la paginación conserva los filtros", () => {
    const f = parseFilters({ fit_tier: "B", rising: "1", p: "3" });
    expect(toQuery(f, 4)).toBe("fit_tier=B&rising=1&sort=intent&dir=desc&p=4");
  });
});
