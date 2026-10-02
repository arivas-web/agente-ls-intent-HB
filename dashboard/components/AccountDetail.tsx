import { LineChart } from "./Charts";
import { Badge, Empty, d10, n0, n1, show, StatusBadge } from "./ui";
import { OUTCOME_LABEL, ORIGIN_LABEL } from "@/lib/config";
import type { AccountData } from "@/lib/account";
import type { Signal } from "@/lib/types";

const MAX_SIGNALS = 60;

function SignalsTable({ signals, who }: { signals: Signal[] | undefined; who: (id: string | null | undefined) => string }) {
  if (!signals?.length) return <Empty>Sin señales.</Empty>;
  const sorted = [...signals].sort((a, b) => (b.at ?? "").localeCompare(a.at ?? ""));
  return (
    <div className="table-wrap">
      <table>
        <thead><tr><th>Fecha</th><th>Contacto</th><th>Tipo</th><th>URL / acción</th><th className="num">Puntos base</th><th className="num">Puntos (con decaimiento)</th></tr></thead>
        <tbody>
          {sorted.slice(0, MAX_SIGNALS).map((s, i) => (
            <tr key={i}>
              <td>{d10(s.at)}</td><td className="wrap">{who(s.contact_id)}</td><td>{s.type ?? "—"}</td>
              <td className="wrap">{s.object ? (/^https?:/.test(s.object) ? <a href={s.object} target="_blank" rel="noreferrer">{s.object}</a> : s.object) : "—"}</td>
              <td className="num">{n1(s.raw_points)}</td><td className="num">{n1(s.points)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {sorted.length > MAX_SIGNALS && <p className="muted small" style={{ padding: "0 10px" }}>Mostrando {MAX_SIGNALS} de {sorted.length} señales (las más recientes).</p>}
    </div>
  );
}

export default function AccountDetail({ data, showHistory = false }: { data: AccountData; showHistory?: boolean }) {
  const { company, score, contacts, contactScores, opps, assignment } = data;
  const bd = score?.breakdown ?? {};
  const byId = new Map(contacts.map((c) => [c.hs_id, c]));
  const who = (id: string | null | undefined) => (id ? byId.get(id)?.email ?? id : "—");
  const claude = assignment?.claude ?? null;
  const fit = bd.fit ?? {};
  const prov = fit.proveedor ?? {};

  return (
    <div>
      <div className="card">
        <h1>{company.name ?? company.hs_id}</h1>
        <dl className="kv">
          <dt>Dominio</dt><dd>{show(company.domain)}</dd>
          <dt>Target market</dt><dd>{show(company.target_market)}</dd>
          <dt>Proveedor actual</dt><dd>{show(company.proveedor)}</dd>
          <dt>País</dt><dd>{show(company.pais)}</dd>
          <dt>Estado</dt><dd>{show(company.status)} {company.tipo_de_contacto ? `· ${company.tipo_de_contacto}` : ""}</dd>
          <dt>Última actividad</dt><dd>{d10(company.last_activity_at)}</dd>
          <dt>Foto de puntuación</dt><dd>{score ? d10(score.date) : "Sin puntuación"}</dd>
        </dl>
        {score && (
          <p>
            <Badge tone="accent">Prioridad {score.priority ?? "—"}</Badge>{" "}
            <Badge>Fit {n0(score.fit)} ({score.fit_tier ?? "—"})</Badge>{" "}
            <Badge>Engagement {n0(score.engagement)}</Badge>{" "}
            <Badge>Intención {n0(score.intent)} (nivel {score.intent_tier ?? "—"})</Badge>{" "}
            <Badge>Velocidad {n1(score.intent_velocity)}</Badge>{" "}
            {score.action && <Badge>{score.action}</Badge>}{" "}
            {score.missing_decision_maker && <Badge tone="warn">Falta decisor</Badge>}
            {bd.intent?.frozen && <> <Badge tone="warn">Intención congelada</Badge></>}
          </p>
        )}
      </div>

      {claude ? (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>Resumen de Claude</h2>
          <dl className="kv">
            <dt>Por qué ahora</dt><dd className="pre">{show(claude.vt_why_now)}</dd>
            <dt>Ángulo y objeción</dt><dd className="pre">{show(claude.vt_angle)}</dd>
            <dt>Contacto recomendado</dt><dd className="pre">{show(claude.contact_justification)}</dd>
            <dt>Intención IA</dt><dd>{claude.vt_ai_intent ? `${claude.vt_ai_intent}/5` : "—"}{claude.vt_ai_intent_reason ? ` · ${claude.vt_ai_intent_reason}` : ""}</dd>
          </dl>
        </div>
      ) : (
        <p className="muted">Sin resumen de Claude para esta cuenta{assignment ? " (cuenta sustituida o añadida a mano)" : ""}.</p>
      )}

      <h2>Fit</h2>
      {score ? (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Criterio</th><th>Valor que lo genera</th><th className="num">Puntos</th></tr></thead>
            <tbody>
              <tr><td>Target market</td><td>{show(fit.target_market?.value)}</td><td className="num">{n1(fit.target_market?.points)}</td></tr>
              <tr>
                <td>Proveedor</td>
                <td className="wrap">{show(prov.value)}{prov.canonico ? ` → ${show(prov.canonico)}` : ""}{prov.metodo ? ` (${show(prov.metodo)})` : ""}{prov.multiples ? ` · múltiples: ${show(prov.multiples)}` : ""}</td>
                <td className="num">{n1(prov.points)}</td>
              </tr>
              <tr><td>Ubicación</td><td>{show(fit.ubicacion?.value)}</td><td className="num">{n1(fit.ubicacion?.points)}</td></tr>
              <tr><td><strong>Total fit</strong></td><td>Nivel {score.fit_tier ?? "—"}</td><td className="num"><strong>{n0(score.fit)}</strong></td></tr>
            </tbody>
          </table>
        </div>
      ) : <Empty>Esta cuenta aún no tiene puntuación.</Empty>}

      <h2>Intención {score ? `(${n0(score.intent)}, nivel ${score.intent_tier ?? "—"})` : ""}</h2>
      <SignalsTable signals={bd.intent?.signals} who={who} />

      <h2>Engagement {score ? `(${n0(score.engagement)})` : ""}</h2>
      {bd.engagement && (
        <p className="muted small">
          Bruto {n1(bd.engagement.raw)} · contactos activos {show(bd.engagement.active_contacts)} · multiplicador por amplitud {show(bd.engagement.breadth_multiplier)}
        </p>
      )}
      <SignalsTable signals={bd.engagement?.signals} who={who} />

      <h2>Contactos</h2>
      {contacts.length ? (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Contacto</th><th>Cargo</th><th className="num">Persona</th><th className="num">Cargo</th><th className="num">Engagement</th><th className="num">Contactab.</th><th>Buyer persona sugerido</th></tr></thead>
            <tbody>
              {contacts.map((c) => {
                const cs = contactScores.get(c.hs_id);
                return (
                  <tr key={c.hs_id}>
                    <td className="wrap">{c.email ?? c.hs_id} {score?.best_contact === c.hs_id && <Badge tone="accent">Recomendado</Badge>} {c.excluded && <Badge>Excluido</Badge>}</td>
                    <td>{show(c.cargo_icp)}</td>
                    <td className="num">{n1(cs?.persona)}</td>
                    <td className="num">{n1(cs?.breakdown?.cargo)}</td>
                    <td className="num">{n1(cs?.breakdown?.engagement)}</td>
                    <td className="num">{n1(cs?.breakdown?.contactabilidad)}</td>
                    <td>{claude?.buyer_persona_suggested?.[c.hs_id] ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : <Empty>Sin contactos.</Empty>}

      <h2>Gestiones de Venzo</h2>
      {opps.length ? (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Etapa</th><th>Estado</th><th>Motivo</th><th>Abierta</th><th>Cerrada</th><th>Última gestión</th></tr></thead>
            <tbody>
              {opps.map((o) => (
                <tr key={o.id}>
                  <td>{show(o.stage)}</td>
                  <td>{o.status_norm ? <Badge tone={o.status_norm === "ganada" ? "ok" : o.status_norm === "perdida" ? "bad" : "warn"}>{o.status_norm}</Badge> : show(o.status)}</td>
                  <td>{show(o.loss_reason)}</td><td>{d10(o.opened_at)}</td><td>{d10(o.closed_at)}</td>
                  <td className="wrap">{show(o.last_management)} {o.last_management_at ? `(${d10(o.last_management_at)})` : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <Empty>Sin oportunidades en Venzo para esta empresa.</Empty>}

      {showHistory && (
        <>
          <h2>Evolución histórica</h2>
          <div className="card">
            <LineChart
              series={[
                { name: "Fit", color: "#1d4ed8", points: data.history.map((h) => ({ x: h.date, y: h.fit === null ? null : Number(h.fit) })) },
                { name: "Engagement", color: "#374151", dash: "5 3", points: data.history.map((h) => ({ x: h.date, y: h.engagement === null ? null : Number(h.engagement) })) },
                { name: "Intención", color: "#9ca3af", points: data.history.map((h) => ({ x: h.date, y: h.intent === null ? null : Number(h.intent) })) },
              ]}
              yMax={100}
            />
          </div>

          <h2>Historial de asignaciones</h2>
          {data.assignments.length ? (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Semana</th><th>Borrador</th><th>SDR</th><th>Origen</th><th>Grupo</th><th>Estado</th></tr></thead>
                <tbody>
                  {data.assignments.map((a) => (
                    <tr key={a.id}>
                      <td>{d10(a.weekly_drafts?.week)}</td>
                      <td>{a.weekly_drafts ? <StatusBadge status={a.weekly_drafts.status} /> : "—"}</td>
                      <td>{a.sdr}{a.sdr_original && a.sdr_original !== a.sdr ? ` (antes ${a.sdr_original})` : ""}</td>
                      <td>{ORIGIN_LABEL[a.origin ?? ""] ?? show(a.origin)}</td>
                      <td>{a.is_control ? "Control" : "Puntuada"}</td>
                      <td>{a.removed ? <Badge tone="bad">Quitada</Badge> : <Badge tone="ok">Activa</Badge>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <Empty>Nunca ha sido asignada.</Empty>}

          <h2>Llamadas</h2>
          {data.calls.length ? (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Fecha</th><th>SDR</th><th>Contacto</th><th>Resultado</th></tr></thead>
                <tbody>
                  {data.calls.map((c) => (
                    <tr key={c.id}><td>{d10(c.at)}</td><td>{show(c.sdr)}</td><td className="wrap">{who(c.contact_hs_id)}</td><td>{OUTCOME_LABEL[c.outcome ?? ""] ?? show(c.outcome)}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <Empty>Sin llamadas registradas.</Empty>}
        </>
      )}
    </div>
  );
}
