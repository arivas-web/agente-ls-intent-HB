import { ago, type Activity } from "@/lib/activity";

const HEAT: Record<string, string> = { hot: "Intención alta", warm: "Interés" };

export default function ActivityFeed({ items, who, limit = 12 }: { items: Activity[]; who?: (id: string | null) => string; limit?: number }) {
  if (!items.length) return <p className="muted">Sin actividad registrada todavía.</p>;
  return (
    <ul className="feed">
      {items.slice(0, limit).map((a, i) => (
        <li key={i} className={a.tone}>
          <span className="ic" aria-hidden>{a.icon}</span>
          <div>
            <span className="tx">{a.text}</span>
            {HEAT[a.tone] && <span className="heat">{HEAT[a.tone]}</span>}
            {(a.detail || (who && a.contact_id)) && (
              <div className="muted small">{[who && a.contact_id ? who(a.contact_id) : null, a.detail].filter(Boolean).join(" · ")}</div>
            )}
          </div>
          <span className="when" title={a.at.slice(0, 10)}>{ago(a.at)}</span>
        </li>
      ))}
      {items.length > limit && <li className="muted small" style={{ gridTemplateColumns: "1fr" }}>+ {items.length - limit} acciones más antiguas</li>}
    </ul>
  );
}
