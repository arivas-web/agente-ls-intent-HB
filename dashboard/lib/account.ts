import { fetchAll, latestScoreDate, type Sb } from "./db";
import type { Assignment, CallOutcome, Company, Contact, ContactScore, Draft, Opportunity, ScoreRow } from "./types";

export interface AssignmentWithDraft extends Assignment {
  weekly_drafts: Pick<Draft, "week" | "status"> | null;
}
export interface AccountData {
  company: Company;
  score: ScoreRow | null;
  history: Pick<ScoreRow, "date" | "fit" | "engagement" | "intent">[];
  contacts: Contact[];
  contactScores: Map<string, ContactScore>;
  opps: Opportunity[];
  assignments: AssignmentWithDraft[];
  calls: CallOutcome[];
  /** Asignación cuyo resumen de Claude se muestra (la del borrador pedido o la más reciente con resumen). */
  assignment: AssignmentWithDraft | null;
}

export async function loadAccount(sb: Sb, id: string, draftId?: number | null): Promise<AccountData | null> {
  const { data: company, error } = await sb.from("companies").select("*").eq("hs_id", id).maybeSingle();
  if (error) throw new Error(error.message);
  if (!company) return null;
  const date = await latestScoreDate(sb);

  const [history, contacts, opps, assignments, calls] = await Promise.all([
    fetchAll<AccountData["history"][number]>((f, t) =>
      sb.from("company_scores_daily").select("date,fit,engagement,intent").eq("company_hs_id", id).order("date").range(f, t)),
    fetchAll<Contact>((f, t) => sb.from("contacts").select("*").eq("company_hs_id", id).range(f, t)),
    fetchAll<Opportunity>((f, t) => sb.from("opportunities").select("*").eq("company_hs_id", id).order("opened_at", { ascending: false }).range(f, t)),
    fetchAll<AssignmentWithDraft>((f, t) =>
      sb.from("weekly_assignments").select("*, weekly_drafts(week,status)").eq("company_hs_id", id).range(f, t)),
    fetchAll<CallOutcome>((f, t) => sb.from("call_outcomes").select("*").eq("company_hs_id", id).order("at", { ascending: false }).range(f, t)),
  ]);
  assignments.sort((a, b) => (b.weekly_drafts?.week ?? "").localeCompare(a.weekly_drafts?.week ?? ""));

  let score: ScoreRow | null = null;
  const contactScores = new Map<string, ContactScore>();
  if (date) {
    const { data: s } = await sb.from("company_scores_daily").select("*").eq("date", date).eq("company_hs_id", id).maybeSingle();
    score = (s as ScoreRow | null) ?? null;
    if (!score && history.length) {
      const last = history[history.length - 1].date;
      const { data: s2 } = await sb.from("company_scores_daily").select("*").eq("date", last).eq("company_hs_id", id).maybeSingle();
      score = (s2 as ScoreRow | null) ?? null;
    }
    if (score) {
      const cs = await fetchAll<ContactScore>((f, t) =>
        sb.from("contact_scores_daily").select("*").eq("date", score!.date).eq("company_hs_id", id).range(f, t));
      cs.forEach((c) => contactScores.set(c.contact_hs_id, c));
    }
  }
  const assignment =
    (draftId ? assignments.find((a) => a.draft_id === draftId) : undefined) ??
    assignments.find((a) => !a.removed && a.claude) ??
    null;
  return { company: company as Company, score, history, contacts, contactScores, opps, assignments, calls, assignment };
}
