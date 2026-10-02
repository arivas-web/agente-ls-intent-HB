import { DRAFT_STATUS_LABEL, DRAFT_STATUS_TONE } from "@/lib/config";
import { qualityOf } from "@/lib/activity";

export function Badge({ tone = "neutral", children }: { tone?: "ok" | "warn" | "bad" | "neutral" | "accent"; children: React.ReactNode }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={DRAFT_STATUS_TONE[status] ?? "neutral"}>{DRAFT_STATUS_LABEL[status] ?? status}</Badge>;
}
export const n0 = (v: number | null | undefined) => (v === null || v === undefined ? "—" : String(Math.round(Number(v))));
export const n1 = (v: number | null | undefined) => (v === null || v === undefined ? "—" : String(Math.round(Number(v) * 10) / 10));
export const d10 = (v: string | null | undefined) => (v ? v.slice(0, 10) : "—");
export function show(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "string" || typeof v === "number" || typeof v === "boolean") return String(v);
  return JSON.stringify(v);
}
export function short(s: string | null | undefined, n = 110): string {
  if (!s) return "—";
  return s.length > n ? s.slice(0, n - 1).trimEnd() + "…" : s;
}
export function Empty({ children }: { children: React.ReactNode }) {
  return <p className="muted">{children}</p>;
}
export function DbError({ error }: { error: unknown }) {
  return <div className="notice bad">Error al leer datos: {error instanceof Error ? error.message : String(error)}</div>;
}

/** Calidad de la cuenta a simple vista: texto + medidor de 4 puntos. */
export function QualityBadge({ priority, title }: { priority: string | null | undefined; title?: boolean }) {
  const q = qualityOf(priority);
  return (
    <span className={`qual ${q.tone}`} title={title === false ? undefined : q.hint}>
      <span className="dots">{[1, 2, 3, 4].map((i) => <i key={i} className={i <= q.level ? "on" : ""} />)}</span>
      {q.label}
    </span>
  );
}

export function Meter({ label, value }: { label: string; value: number | null | undefined }) {
  const v = Math.max(0, Math.min(100, Number(value ?? 0)));
  return (
    <div className="meter">
      <span>{label}</span>
      <div className="track"><div className="fill" style={{ width: `${v}%` }} /></div>
      <span className="v">{value === null || value === undefined ? "—" : Math.round(v)}</span>
    </div>
  );
}
export function Meters({ fit, engagement, intent }: { fit: number | null | undefined; engagement: number | null | undefined; intent: number | null | undefined }) {
  return (
    <div className="meters">
      <Meter label="Perfil" value={fit} /><Meter label="Actividad" value={engagement} /><Meter label="Intención" value={intent} />
    </div>
  );
}
