export interface Company {
  hs_id: string;
  name: string | null;
  domain: string | null;
  target_market: string | null;
  proveedor: string | null;
  pais: string | null;
  status: string | null;
  tipo_de_contacto: string | null;
  last_activity_at: string | null;
}
export interface Contact {
  hs_id: string;
  company_hs_id: string;
  email: string | null;
  cargo_icp: string | null;
  phones: string[] | null;
  linkedin_url: string | null;
  excluded: boolean | null;
}
export interface Signal {
  contact_id?: string | null;
  type?: string;
  object?: string | null;
  at?: string;
  raw_points?: number;
  points?: number;
}
export interface Breakdown {
  fit?: {
    target_market?: { value?: unknown; points?: number };
    proveedor?: { value?: unknown; canonico?: unknown; metodo?: unknown; points?: number; multiples?: unknown };
    ubicacion?: { value?: unknown; points?: number };
  };
  engagement?: {
    score?: number;
    raw?: number;
    active_contacts?: number;
    breadth_multiplier?: number;
    contacts?: Record<string, { points?: number; cargo_categoria?: string; cargo_mult?: number; active?: boolean }>;
    signals?: Signal[];
  };
  intent?: { score?: number; tier?: number; frozen?: boolean; signals?: Signal[] };
  action?: string;
}
export interface ScoreRow {
  date: string;
  company_hs_id: string;
  fit: number | null;
  fit_tier: string | null;
  engagement: number | null;
  intent: number | null;
  intent_tier: number | null;
  intent_velocity: number | null;
  priority: string | null;
  action: string | null;
  best_contact: string | null;
  missing_decision_maker: boolean | null;
  breakdown: Breakdown | null;
}
export interface ContactScore {
  contact_hs_id: string;
  company_hs_id: string;
  persona: number | null;
  breakdown: { cargo?: number; engagement?: number; contactabilidad?: number } | null;
}
export interface Claude {
  vt_why_now?: string;
  vt_angle?: string;
  contact_justification?: string;
  vt_ai_intent?: number;
  vt_ai_intent_reason?: string;
  buyer_persona_suggested?: Record<string, string>;
}
export interface EditLogEntry {
  at: string;
  action: string;
  detail: string;
}
export interface Draft {
  id: number;
  week: string;
  status: "pendiente_validar" | "validado" | "enviado" | "no_enviado";
  created_at: string | null;
  validated_at: string | null;
  sent_at: string | null;
}
export interface Assignment {
  id: number;
  draft_id: number;
  company_hs_id: string;
  sdr: string;
  rank: number | null;
  is_control: boolean;
  origin: string | null;
  claude: Claude | null;
  user_edit: string | null;
  edit_log: EditLogEntry[] | null;
  removed: boolean;
  sdr_original: string | null;
  added_manually: boolean | null;
}
export interface Candidate {
  draft_id: number;
  company_hs_id: string;
  rank: number;
  code: string | null;
  fit: number | null;
  intent: number | null;
  engagement: number | null;
  velocity: number | null;
  is_control_pool: boolean | null;
}
export interface Opportunity {
  id: string;
  company_hs_id: string | null;
  stage: string | null;
  status: string | null;
  status_norm: "abierta" | "ganada" | "perdida" | null;
  loss_reason: string | null;
  opened_at: string | null;
  closed_at: string | null;
  origin: string | null;
  amount: number | null;
  last_management: string | null;
  last_management_at: string | null;
}
export interface CallOutcome {
  id: number;
  company_hs_id: string;
  contact_hs_id: string | null;
  sdr: string | null;
  at: string;
  outcome: string | null;
}
