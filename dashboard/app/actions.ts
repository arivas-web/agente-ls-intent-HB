"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { SDRS } from "@/lib/config";
import { safeLike, type Sb } from "@/lib/db";
import type { Assignment, Candidate, Draft, EditLogEntry } from "@/lib/types";

export interface ActionResult {
  ok: boolean;
  error?: string;
}
const fail = (error: string): ActionResult => ({ ok: false, error });
const entry = (action: string, detail: string): EditLogEntry => ({ at: new Date().toISOString(), action, detail });

async function loadEditable(sb: Sb, assignmentId: number): Promise<{ a: Assignment; d: Draft } | string> {
  const { data: a, error } = await sb.from("weekly_assignments").select("*").eq("id", assignmentId).single();
  if (error || !a) return "Asignación no encontrada";
  const { data: d } = await sb.from("weekly_drafts").select("*").eq("id", (a as Assignment).draft_id).single();
  if (!d) return "Borrador no encontrado";
  if ((d as Draft).status === "enviado" || (d as Draft).status === "no_enviado") return "El borrador es de solo lectura";
  return { a: a as Assignment, d: d as Draft };
}

async function appendLog(sb: Sb, id: number, current: EditLogEntry[] | null, e: EditLogEntry, extra: Record<string, unknown> = {}) {
  return sb.from("weekly_assignments").update({ ...extra, edit_log: [...(current ?? []), e] }).eq("id", id);
}

export async function removeAssignment(assignmentId: number): Promise<ActionResult> {
  const sb = createClient();
  const r = await loadEditable(sb, assignmentId);
  if (typeof r === "string") return fail(r);
  const { error } = await appendLog(sb, r.a.id, r.a.edit_log, entry("quitar", `Cuenta ${r.a.company_hs_id} quitada de ${r.a.sdr}`), { removed: true });
  if (error) return fail(error.message);
  revalidatePath("/");
  return { ok: true };
}

export async function replaceAssignment(assignmentId: number): Promise<ActionResult> {
  const sb = createClient();
  const r = await loadEditable(sb, assignmentId);
  if (typeof r === "string") return fail(r);
  const { a } = r;
  const { data: all } = await sb.from("weekly_assignments").select("company_hs_id").eq("draft_id", a.draft_id);
  const inDraft = new Set((all ?? []).map((x: { company_hs_id: string }) => x.company_hs_id));
  const { data: cur } = await sb.from("draft_candidates").select("rank").eq("draft_id", a.draft_id).eq("company_hs_id", a.company_hs_id).maybeSingle();
  const curRank = (cur as { rank: number } | null)?.rank ?? 0; // si no viene de la lista de candidatos, se parte del principio
  const { data: cands, error: ce } = await sb
    .from("draft_candidates").select("*").eq("draft_id", a.draft_id).gt("rank", curRank)
    .eq("is_control_pool", a.is_control).order("rank", { ascending: true }).limit(500);
  if (ce) return fail(ce.message);
  const next = ((cands ?? []) as Candidate[]).find((c) => !inDraft.has(c.company_hs_id));
  if (!next) return fail("No quedan candidatos en la lista del borrador");
  const { error: e1 } = await appendLog(sb, a.id, a.edit_log, entry("sustituir", `Sustituida por ${next.company_hs_id} (rank ${next.rank})`), { removed: true });
  if (e1) return fail(e1.message);
  const { error: e2 } = await sb.from("weekly_assignments").insert({
    draft_id: a.draft_id, company_hs_id: next.company_hs_id, sdr: a.sdr, rank: next.rank,
    is_control: a.is_control, origin: a.is_control ? "control" : "scored", claude: null,
    edit_log: [entry("sustituir", `Entra en lugar de ${a.company_hs_id}`)], removed: false,
  });
  if (e2) return fail(e2.message);
  revalidatePath("/");
  return { ok: true };
}

export async function changeSdr(assignmentId: number, sdr: string): Promise<ActionResult> {
  if (!(SDRS as readonly string[]).includes(sdr)) return fail("SDR no válido");
  const sb = createClient();
  const r = await loadEditable(sb, assignmentId);
  if (typeof r === "string") return fail(r);
  if (r.a.sdr === sdr) return { ok: true };
  const { error } = await appendLog(sb, r.a.id, r.a.edit_log, entry("cambiar_sdr", `${r.a.sdr} -> ${sdr}`), {
    sdr, sdr_original: r.a.sdr_original ?? r.a.sdr,
  });
  if (error) return fail(error.message);
  revalidatePath("/");
  return { ok: true };
}

export async function addManual(draftId: number, companyId: string, sdr: string): Promise<ActionResult> {
  if (!(SDRS as readonly string[]).includes(sdr)) return fail("SDR no válido");
  const sb = createClient();
  const { data: d } = await sb.from("weekly_drafts").select("*").eq("id", draftId).single();
  if (!d) return fail("Borrador no encontrado");
  if ((d as Draft).status === "enviado" || (d as Draft).status === "no_enviado") return fail("El borrador es de solo lectura");
  const e = entry("añadir_manual", `Añadida manualmente a ${sdr}`);
  const { data: ex } = await sb.from("weekly_assignments").select("*").eq("draft_id", draftId).eq("company_hs_id", companyId).maybeSingle();
  if (ex) {
    const a = ex as Assignment;
    if (!a.removed) return fail("La cuenta ya está en el borrador");
    const { error } = await appendLog(sb, a.id, a.edit_log, e, { removed: false, sdr, added_manually: true, sdr_original: a.sdr_original ?? a.sdr });
    if (error) return fail(error.message);
  } else {
    const { error } = await sb.from("weekly_assignments").insert({
      draft_id: draftId, company_hs_id: companyId, sdr, rank: null, is_control: false, origin: "manual",
      added_manually: true, removed: false, edit_log: [e],
    });
    if (error) return fail(error.message);
  }
  revalidatePath("/");
  return { ok: true };
}

export async function validateWeek(draftId: number): Promise<ActionResult> {
  const sb = createClient();
  const { data: d } = await sb.from("weekly_drafts").select("status").eq("id", draftId).single();
  if (!d) return fail("Borrador no encontrado");
  if ((d as { status: string }).status !== "pendiente_validar") return fail("Solo se puede validar un borrador pendiente");
  const { error } = await sb.from("weekly_drafts").update({ status: "validado", validated_at: new Date().toISOString() }).eq("id", draftId);
  if (error) return fail(error.message);
  revalidatePath("/");
  return { ok: true };
}

export async function searchCompanies(q: string): Promise<{ hs_id: string; name: string | null; domain: string | null }[]> {
  const s = safeLike(q);
  if (s.length < 2) return [];
  const sb = createClient();
  const { data } = await sb.from("companies").select("hs_id,name,domain").eq("internal", false).ilike("name", `%${s}%`).order("name").limit(15);
  return (data ?? []) as { hs_id: string; name: string | null; domain: string | null }[];
}
