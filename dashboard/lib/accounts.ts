/** Filtros de la pestaña Cuentas (puntuación e interacción). Puro y testeable. */
export const SORTS: Record<string, string> = {
  intent: "Intención", fit: "Fit", engagement: "Engagement", intent_velocity: "Velocidad de intención",
  last_signal_at: "Última interacción", signals_30d: "Interacciones 30 días", name: "Nombre",
};
export const FIT_TIERS = ["A", "B", "C"];
export const INTENT_TIERS = ["1", "2", "3"];
export const INTERACTION: Record<string, string> = {
  "": "Cualquiera", "7d": "Con interacción en 7 días", "30d": "Con interacción en 30 días", none: "Sin interacción en 30 días",
};
/** Estados que no se muestran en Cuentas (cambiar aquí si hace falta). */
export const HIDDEN_STATUSES = ["Account"];
export const STATUSES = ["On Prospection", "Contacted", "Engaged", "Meeting", "Client", "Nurturing", "Delivered",
  "On Hold", "Backlog", "Discarded", "Discovery", "Negociación", "Demo"];
export const TARGETS = ["Transitario PYME", "Transitario + Aduanas", "Consignatarios PYME", "Aduanas PYME", "Depósito aduanero",
  "Shipper/ Consignee", "Operador logístico PYME (transitario terrestre +almacén)", "Transporte terrestre",
  "Agencia de transportes", "Courier", "Otros"];

export interface Filters {
  q: string; fit_tier: string; priority: string; intent_tier: string;
  fit_min?: number; eng_min?: number; int_min?: number; rising: boolean;
  inter: string; visits_min?: number; clicks_min?: number; contacts_min?: number;
  status: string; target: string; sort: string; dir: "asc" | "desc"; page: number;
}

type SP = Record<string, string | string[] | undefined>;
const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? "";
const num = (v: string) => (v.trim() !== "" && Number.isFinite(Number(v)) ? Number(v) : undefined);
const clean = (v: string) => v.replace(/[%_,()*\\]/g, " ").replace(/\s+/g, " ").trim();

export function parseFilters(sp: SP): Filters {
  const sort = one(sp.sort);
  return {
    q: clean(one(sp.q)),
    fit_tier: FIT_TIERS.includes(one(sp.fit_tier)) ? one(sp.fit_tier) : "",
    priority: /^[ABC][123]$/.test(one(sp.priority)) ? one(sp.priority) : "",
    intent_tier: INTENT_TIERS.includes(one(sp.intent_tier)) ? one(sp.intent_tier) : "",
    fit_min: num(one(sp.fit_min)), eng_min: num(one(sp.eng_min)), int_min: num(one(sp.int_min)),
    rising: one(sp.rising) === "1",
    inter: one(sp.inter) in INTERACTION ? one(sp.inter) : "",
    visits_min: num(one(sp.visits_min)), clicks_min: num(one(sp.clicks_min)), contacts_min: num(one(sp.contacts_min)),
    status: STATUSES.includes(one(sp.status)) ? one(sp.status) : "",
    target: TARGETS.includes(one(sp.target)) ? one(sp.target) : "",
    sort: sort in SORTS ? sort : "intent",
    dir: one(sp.dir) === "asc" ? "asc" : "desc",
    page: Math.max(1, Math.floor(Number(one(sp.p))) || 1),
  };
}

/** Aplica los filtros a una consulta de PostgREST (tipo mínimo para poder probarlo sin red). */
export interface Q {
  or(f: string): Q; eq(c: string, v: string | number): Q; gte(c: string, v: number): Q; gt(c: string, v: number): Q;
}
export function applyFilters<T extends Q>(query: T, f: Filters): T {
  let x: Q = query;
  x = x.or(`status.is.null,status.not.in.(${HIDDEN_STATUSES.join(",")})`);   // sin estado o distinto de los ocultos
  if (f.q) x = x.or(`name.ilike.%${f.q}%,domain.ilike.%${f.q}%`);
  if (f.fit_tier) x = x.eq("fit_tier", f.fit_tier);
  if (f.priority) x = x.eq("priority", f.priority);
  if (f.intent_tier) x = x.eq("intent_tier", Number(f.intent_tier));
  if (f.fit_min !== undefined) x = x.gte("fit", f.fit_min);
  if (f.eng_min !== undefined) x = x.gte("engagement", f.eng_min);
  if (f.int_min !== undefined) x = x.gte("intent", f.int_min);
  if (f.rising) x = x.gt("intent_velocity", 0);
  if (f.inter === "7d") x = x.gte("signals_7d", 1);
  if (f.inter === "30d") x = x.gte("signals_30d", 1);
  if (f.inter === "none") x = x.eq("signals_30d", 0);
  if (f.visits_min !== undefined) x = x.gte("visits_30d", f.visits_min);
  if (f.clicks_min !== undefined) x = x.gte("email_clicks_30d", f.clicks_min);
  if (f.contacts_min !== undefined) x = x.gte("active_contacts_30d", f.contacts_min);
  if (f.status) x = x.eq("status", f.status);
  if (f.target) x = x.eq("target_market", f.target);
  return x as T;
}

/** Querystring con los filtros activos (para paginar manteniéndolos). */
export function toQuery(f: Filters, page: number): string {
  const p = new URLSearchParams();
  const set = (k: string, v: string | number | undefined | boolean) => { if (v !== undefined && v !== "" && v !== false) p.set(k, v === true ? "1" : String(v)); };
  set("q", f.q); set("fit_tier", f.fit_tier); set("priority", f.priority); set("intent_tier", f.intent_tier);
  set("fit_min", f.fit_min); set("eng_min", f.eng_min); set("int_min", f.int_min); set("rising", f.rising);
  set("inter", f.inter); set("visits_min", f.visits_min); set("clicks_min", f.clicks_min); set("contacts_min", f.contacts_min);
  set("status", f.status); set("target", f.target); set("sort", f.sort); set("dir", f.dir);
  if (page > 1) p.set("p", String(page));
  return p.toString();
}
