import { describe, expect, it } from "vitest";
import { ago, describeSignal, oneLiner, qualityOf, toActivities } from "./activity";

describe("activity", () => {
  it("traduce visitas a frases", () => {
    expect(describeSignal({ type: "web_visit", object: "/precios/" }).text).toBe("Miró la página de precios");
    expect(describeSignal({ type: "web_visit", object: "/productos/suite/" }).text).toContain("Visual Trans Suite");
    expect(describeSignal({ type: "web_visit", object: "/noticias/como-elegir-erp/" }).text).toContain("Como elegir erp");
    expect(describeSignal({ type: "web_visit", object: "/otra-cosa/" }).text).toBe("Visitó la web");
  });
  it("traduce tipos especiales y no deja códigos crudos", () => {
    expect(describeSignal({ type: "email_click" }).text).toMatch(/correo/);
    expect(describeSignal({ type: "reply_detected" }).tone).toBe("hot");
    expect(describeSignal({ type: "tipo_raro_nuevo" }).text).toBe("Tipo raro nuevo");
  });
  it("oculta sesiones sueltas y ordena por fecha", () => {
    const a = toActivities([
      { type: "session", at: "2026-10-01T00:00:00Z" },
      { type: "email_click", at: "2026-09-01T00:00:00Z" },
      { type: "web_visit", object: "/precios/", at: "2026-09-20T00:00:00Z" },
    ]);
    expect(a.map((x) => x.at.slice(0, 10))).toEqual(["2026-09-20", "2026-09-01"]);
  });
  it("calidad y resumen", () => {
    expect(qualityOf("A1").label).toBe("Excelente");
    expect(qualityOf(null).tone).toBe("none");
    expect(oneLiner([])).toBe("Sin actividad reciente");
    const now = new Date("2026-10-02T00:00:00Z");
    expect(ago("2026-09-29T00:00:00Z", now)).toBe("hace 3 días");
    expect(oneLiner(toActivities([{ type: "web_visit", object: "/precios/", at: "2026-09-29T00:00:00Z" }]), now)).toBe("Miró la página de precios · última hace 3 días");
  });
});
