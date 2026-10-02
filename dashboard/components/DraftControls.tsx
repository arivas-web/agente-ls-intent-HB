"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { addManual, changeSdr, removeAssignment, replaceAssignment, searchCompanies, validateWeek, type ActionResult } from "@/app/actions";
import { SDRS } from "@/lib/config";

function useRun() {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const run = (fn: () => Promise<ActionResult>, confirmMsg?: string) => {
    if (confirmMsg && !window.confirm(confirmMsg)) return;
    setError(null);
    start(async () => {
      const r = await fn();
      if (!r.ok) setError(r.error ?? "Error");
      router.refresh();
    });
  };
  return { pending, error, run };
}

export function RowActions({ id, sdr, name }: { id: number; sdr: string; name: string }) {
  const { pending, error, run } = useRun();
  const other = SDRS.find((s) => s !== sdr) ?? SDRS[0];
  return (
    <div>
      <button type="button" className="link danger" disabled={pending} onClick={() => run(() => removeAssignment(id), `¿Quitar "${name}" de la semana?`)}>Quitar</button>
      <button type="button" className="link" disabled={pending} onClick={() => run(() => replaceAssignment(id), `¿Sustituir "${name}" por la siguiente de la lista?`)}>Sustituir</button>
      <button type="button" className="link" disabled={pending} onClick={() => run(() => changeSdr(id, other))}>Pasar a {other}</button>
      {error && <div className="small" style={{ color: "var(--bad)" }}>{error}</div>}
    </div>
  );
}

export function ValidateButton({ draftId, summary }: { draftId: number; summary: string }) {
  const { pending, error, run } = useRun();
  return (
    <span>
      <button type="button" className="primary" disabled={pending} onClick={() => run(() => validateWeek(draftId), `¿Validar la semana?\n\n${summary}\n\nDespués se enviará el lunes.`)}>
        {pending ? "Validando…" : "Validar semana"}
      </button>
      {error && <span className="small" style={{ color: "var(--bad)" }}> {error}</span>}
    </span>
  );
}

export function AddManual({ draftId }: { draftId: number }) {
  const { pending, error, run } = useRun();
  const [q, setQ] = useState("");
  const [results, setResults] = useState<{ hs_id: string; name: string | null; domain: string | null }[]>([]);
  const [chosen, setChosen] = useState<{ hs_id: string; name: string | null } | null>(null);
  const [sdr, setSdr] = useState<string>(SDRS[0]);

  async function buscar(v: string) {
    setQ(v);
    setChosen(null);
    setResults(v.trim().length >= 2 ? await searchCompanies(v) : []);
  }
  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>Añadir cuenta manualmente</h3>
      <div className="row">
        <label className="grow">Empresa (nombre)
          <input value={chosen ? chosen.name ?? chosen.hs_id : q} onChange={(e) => buscar(e.target.value)} placeholder="Buscar empresa…" />
        </label>
        <label>SDR
          <select value={sdr} onChange={(e) => setSdr(e.target.value)}>{SDRS.map((s) => <option key={s}>{s}</option>)}</select>
        </label>
        <button type="button" className="primary" disabled={!chosen || pending}
          onClick={() => chosen && run(async () => { const r = await addManual(draftId, chosen.hs_id, sdr); if (r.ok) { setChosen(null); setQ(""); setResults([]); } return r; })}>
          Añadir
        </button>
      </div>
      {!chosen && results.length > 0 && (
        <ul style={{ margin: 0, paddingLeft: 18 }}>
          {results.map((r) => (
            <li key={r.hs_id}><button type="button" className="link" onClick={() => setChosen(r)}>{r.name ?? r.hs_id}</button> <span className="muted small">{r.domain ?? ""}</span></li>
          ))}
        </ul>
      )}
      {error && <div className="notice bad">{error}</div>}
    </div>
  );
}
