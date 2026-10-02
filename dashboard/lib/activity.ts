import type { Signal } from "./types";

/** Traduce las señales técnicas (web_visit, email_click…) a frases legibles. */

export type Tone = "hot" | "warm" | "mid" | "cold";
export interface Activity {
  icon: string;
  text: string;
  detail?: string;
  /** Peso para ordenar y colorear: intención fuerte > engagement. */
  tone: Tone;
  at: string;
  contact_id: string | null;
  points: number;
}

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const PRODUCTS: Record<string, string> = {
  suite: "Visual Trans Suite", vforwarding: "vForwarding", empuries: "Empúries", virtualdua: "VirtualDUA", "tariff-code": "Tariff Code",
};

function slugTitle(slug: string): string {
  const t = slug.replace(/[-_]+/g, " ").trim();
  return t ? cap(t) : "";
}

interface PageRule { re: RegExp; icon: string; text: (m: RegExpMatchArray) => string; tone: Tone }
const PAGES: PageRule[] = [
  { re: /^\/precios\/$/, icon: "💶", text: () => "Miró la página de precios", tone: "hot" },
  { re: /^\/(solicita-tu-demo|demo-visual-trans)\/$/, icon: "🎯", text: () => "Visitó la página para pedir una demo", tone: "hot" },
  { re: /^\/contactar\/$/, icon: "✉️", text: () => "Visitó la página de contacto", tone: "hot" },
  { re: /^\/(ayudas-y-subvenciones|kit-digital)\/$/, icon: "🏛️", text: () => "Consultó ayudas y subvenciones (Kit Digital)", tone: "hot" },
  { re: /^\/(documento-electronico-de-control-administrativo-deca|autodespacho-inteligente|info-verifactu)\/$|^\/productos\/[^/]+\/verifactu\/$|operativa-deca/, icon: "📜", text: () => "Consultó normativa con plazo (DECA / Verifactu)", tone: "hot" },
  { re: /^\/casos-de-exito\/$/, icon: "🏆", text: () => "Vio el listado de casos de éxito", tone: "warm" },
  { re: /^\/casos-de-exito\/([^/]+)\/$/, icon: "🏆", text: (m) => `Leyó un caso de éxito (${slugTitle(m[1])})`, tone: "hot" },
  { re: /^\/clientes\/$/, icon: "🤝", text: () => "Vio la página de clientes", tone: "warm" },
  { re: /^\/(integraciones|integraciones-webcargo|deiworld)\/$/, icon: "🔌", text: () => "Vio las integraciones", tone: "warm" },
  { re: /^\/productos\/(suite|vforwarding|empuries|virtualdua|tariff-code)\/$/, icon: "📦", text: (m) => `Vio el producto ${PRODUCTS[m[1]] ?? m[1]}`, tone: "warm" },
  { re: /^\/productos\/(suite|vforwarding|empuries|virtualdua)\/(modulos|funcionalidades)(\/.*)?$/, icon: "🧩", text: (m) => `Miró módulos y funcionalidades de ${PRODUCTS[m[1]] ?? m[1]}`, tone: "warm" },
  { re: /^\/productos\/otros(\/.*)?$/, icon: "📦", text: () => "Vio otros productos", tone: "mid" },
  { re: /^\/productos\/$/, icon: "📦", text: () => "Vio el catálogo de productos", tone: "mid" },
  { re: /^\/(transitarios|aduanas|operadores|consignatarios|cargadores|shippers)\/$/, icon: "🧭", text: (m) => `Vio la página para ${m[1]}`, tone: "warm" },
  { re: /^\/(empresa|about|empresa\/internacional)\/$/, icon: "🏢", text: () => "Vio la página de la empresa", tone: "mid" },
  { re: /^\/productos\/[^/]+\/novedades\//, icon: "🆕", text: () => "Leyó novedades de producto", tone: "mid" },
  { re: /^\/recursos-[^/]+\/$|^\/(recursos|biblioteca-de-recursos|incoterms)\/$/, icon: "📚", text: () => "Consultó recursos y guías", tone: "mid" },
  { re: /^\/(noticias|portal-noticias)\/$/, icon: "📰", text: () => "Vio el listado de noticias", tone: "cold" },
  { re: /^\/noticias\/([^/]+)\/$/, icon: "📰", text: (m) => `Leyó una noticia: ${slugTitle(m[1])}`, tone: "cold" },
  { re: /^\/$/, icon: "🌐", text: () => "Visitó la home", tone: "cold" },
];

const SPECIAL: Record<string, { icon: string; text: string; tone: Tone }> = {
  email_click: { icon: "📧", text: "Hizo clic en un correo de marketing", tone: "warm" },
  session: { icon: "🖥️", text: "Nueva sesión en la web", tone: "cold" },
  reply_detected: { icon: "💬", text: "Respondió a un correo comercial", tone: "hot" },
  unsubscribe: { icon: "🚫", text: "Se dio de baja de los correos", tone: "cold" },
  multi_person_7d: { icon: "👥", text: "Varias personas de la empresa activas esta semana", tone: "hot" },
  sessions_7d: { icon: "🔁", text: "Tres o más sesiones web en 7 días", tone: "hot" },
  return_after_90d: { icon: "↩️", text: "Volvió a la web tras más de 90 días", tone: "hot" },
  ruta_evaluacion: { icon: "🧠", text: "Está evaluando: producto y además precio, demo o caso de éxito", tone: "hot" },
  reactivation: { icon: "⚡", text: "Cuenta reactivada tras un periodo de pausa", tone: "hot" },
  positive_reply: { icon: "✅", text: "Respuesta positiva", tone: "hot" },
  trigger_financiacion_licitacion: { icon: "💰", text: "Noticia de financiación o licitación", tone: "hot" },
  trigger_contratacion_roles: { icon: "🧑‍💼", text: "Está contratando perfiles clave", tone: "warm" },
  trigger_expansion_sede: { icon: "📍", text: "Expansión o nueva sede", tone: "warm" },
  trigger_cambio_decisor: { icon: "🔄", text: "Cambio de decisor", tone: "warm" },
};

export function describeSignal(s: Signal): Omit<Activity, "at" | "contact_id" | "points"> {
  const type = s.type ?? "";
  if (type === "web_visit") {
    const path = (s.object ?? "").toLowerCase();
    for (const r of PAGES) {
      const m = path.match(r.re);
      if (m) return { icon: r.icon, text: r.text(m), tone: r.tone };
    }
    return { icon: "🌐", text: "Visitó la web", detail: path || undefined, tone: "cold" };
  }
  const sp = SPECIAL[type];
  if (sp) return { ...sp, detail: type === "sessions_7d" || type === "ruta_evaluacion" ? undefined : undefined };
  return { icon: "•", text: type ? cap(type.replace(/_/g, " ")) : "Actividad", tone: "cold" };
}

/** Señales → actividades legibles, más recientes primero. Las sesiones sueltas (0 pts) se agrupan por día. */
export function toActivities(signals: Signal[] | undefined, opts: { includeSessions?: boolean } = {}): Activity[] {
  const out: Activity[] = [];
  for (const s of signals ?? []) {
    if (s.type === "session" && !opts.includeSessions) continue;
    const d = describeSignal(s);
    out.push({ ...d, at: s.at ?? "", contact_id: s.contact_id ?? null, points: s.points ?? 0 });
  }
  return out.sort((a, b) => b.at.localeCompare(a.at));
}

/** Une intención + engagement sin duplicados evidentes. */
export function mergeActivities(...lists: (Signal[] | undefined)[]): Activity[] {
  return toActivities(lists.flatMap((l) => l ?? []));
}

/** "hace 3 días" a partir de una fecha ISO. */
export function ago(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) return "—";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "—";
  const days = Math.floor((now.getTime() - t) / 86_400_000);
  if (days <= 0) return "hoy";
  if (days === 1) return "ayer";
  if (days < 14) return `hace ${days} días`;
  if (days < 60) return `hace ${Math.round(days / 7)} semanas`;
  if (days < 700) return `hace ${Math.round(days / 30)} meses`;
  return `hace ${Math.round(days / 365)} años`;
}

export interface Quality {
  label: string;
  /** 0–4 para pintar los puntos del medidor. */
  level: number;
  tone: "great" | "good" | "mid" | "low" | "none";
  hint: string;
}

/** Calidad de la cuenta a simple vista, a partir del código de prioridad (nivel de fit + movimiento). */
export function qualityOf(priority: string | null | undefined): Quality {
  switch (priority) {
    case "A1": return { label: "Excelente", level: 4, tone: "great", hint: "Buen perfil y mucho movimiento: llamar ya" };
    case "A2": return { label: "Muy buena", level: 4, tone: "great", hint: "Buen perfil con movimiento: llamar" };
    case "B1": return { label: "Buena", level: 3, tone: "good", hint: "Perfil medio con mucho movimiento: llamar" };
    case "B2": return { label: "Interesante", level: 3, tone: "good", hint: "Perfil medio con algo de movimiento" };
    case "C1": return { label: "Hay movimiento", level: 2, tone: "mid", hint: "Perfil flojo pero se está moviendo" };
    case "C2": return { label: "Algo de movimiento", level: 2, tone: "mid", hint: "Perfil flojo con poco movimiento" };
    case "A3": return { label: "Buen perfil, sin actividad", level: 2, tone: "mid", hint: "Encaja pero no ha hecho nada todavía" };
    case "B3": return { label: "En espera", level: 1, tone: "low", hint: "Ni encaja especialmente ni se mueve" };
    case "C3": return { label: "Descartable", level: 0, tone: "none", hint: "Perfil flojo y sin actividad" };
    default: return { label: "Sin puntuar", level: 0, tone: "none", hint: "Aún no hay puntuación" };
  }
}

/** Resumen de una línea: "Miró precios · 2 clics en correos · última actividad hace 3 días". */
export function oneLiner(acts: Activity[], now: Date = new Date()): string {
  if (!acts.length) return "Sin actividad reciente";
  const strong = acts.filter((a) => a.tone === "hot" || a.tone === "warm");
  const first = (strong[0] ?? acts[0]).text;
  const clicks = acts.filter((a) => a.text.startsWith("Hizo clic")).length;
  const parts = [first];
  if (clicks > 1) parts.push(`${clicks} clics en correos`);
  parts.push(`última ${ago(acts[0].at, now)}`);
  return parts.join(" · ");
}
