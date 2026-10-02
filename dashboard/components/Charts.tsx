/** Gráficos básicos sin dependencias: barras (HTML) y líneas (SVG). */

export function BarChart({ data, empty = "Sin datos" }: { data: { label: string; value: number }[]; empty?: string }) {
  if (!data.length) return <p className="muted">{empty}</p>;
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div className="bars">
      {data.map((d) => (
        <div className="bar" key={d.label}>
          <span className="bar-label" title={d.label}>{d.label}</span>
          <div className="bar-track"><div className="bar-fill" style={{ width: `${(d.value / max) * 100}%` }} /></div>
          <span className="num">{d.value}</span>
        </div>
      ))}
    </div>
  );
}

export interface Series {
  name: string;
  color: string;
  dash?: string;
  points: { x: string; y: number | null }[];
}

export function LineChart({ series, height = 180, yMax }: { series: Series[]; height?: number; yMax?: number }) {
  const xs = [...new Set(series.flatMap((s) => s.points.map((p) => p.x)))].sort();
  if (!xs.length) return <p className="muted">Sin datos</p>;
  const W = 640, H = height, L = 30, R = 10, T = 10, B = 22;
  const max = yMax ?? Math.max(100, ...series.flatMap((s) => s.points.map((p) => p.y ?? 0)));
  const px = (i: number) => (xs.length === 1 ? (L + W - R) / 2 : L + (i / (xs.length - 1)) * (W - L - R));
  const py = (y: number) => T + (1 - y / max) * (H - T - B);
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Evolución">
        {[0, 0.5, 1].map((f) => (
          <g key={f}>
            <line x1={L} x2={W - R} y1={py(max * f)} y2={py(max * f)} stroke="#e5e7eb" />
            <text x={L - 4} y={py(max * f) + 4} fontSize="10" textAnchor="end" fill="#6b7280">{Math.round(max * f)}</text>
          </g>
        ))}
        <text x={L} y={H - 6} fontSize="10" fill="#6b7280">{xs[0]}</text>
        {xs.length > 1 && <text x={W - R} y={H - 6} fontSize="10" textAnchor="end" fill="#6b7280">{xs[xs.length - 1]}</text>}
        {series.map((s) => {
          const pts = s.points.map((p) => ({ i: xs.indexOf(p.x), y: p.y })).filter((p) => p.y !== null);
          const d = pts.map((p, k) => `${k ? "L" : "M"}${px(p.i).toFixed(1)},${py(p.y as number).toFixed(1)}`).join(" ");
          return (
            <g key={s.name}>
              <path d={d} fill="none" stroke={s.color} strokeWidth="2" strokeDasharray={s.dash} />
              {pts.length === 1 && <circle cx={px(pts[0].i)} cy={py(pts[0].y as number)} r="3" fill={s.color} />}
            </g>
          );
        })}
      </svg>
      <div className="legend">
        {series.map((s) => (
          <span key={s.name}><span className="sw" style={{ background: s.color }} />{s.name}</span>
        ))}
      </div>
    </div>
  );
}

/** Mini línea (porcentajes por semana). */
export function Sparkline({ values }: { values: (number | null)[] }) {
  const W = 90, H = 24;
  const valid = values.filter((v): v is number => v !== null);
  if (valid.length < 1) return <span className="muted">—</span>;
  const max = Math.max(...valid, 1);
  const px = (i: number) => (values.length === 1 ? W / 2 : 2 + (i / (values.length - 1)) * (W - 4));
  const py = (v: number) => H - 3 - (v / max) * (H - 6);
  const pts = values.map((v, i) => (v === null ? null : { x: px(i), y: py(v) }));
  let d = "";
  let prev = false;
  pts.forEach((p) => {
    if (p) d += `${prev ? "L" : "M"}${p.x.toFixed(1)},${p.y.toFixed(1)} `;
    prev = !!p;
  });
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Evolución semanal">
      <path d={d} fill="none" stroke="#1d4ed8" strokeWidth="1.5" />
      {valid.length === 1 && pts.map((p, i) => p && <circle key={i} cx={p.x} cy={p.y} r="2" fill="#1d4ed8" />)}
    </svg>
  );
}
