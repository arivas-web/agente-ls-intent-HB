/** Cuentas por SDR y semana (config/assignment.yaml: accounts_per_sdr_per_week). */
export const ACCOUNTS_PER_SDR = 10;
export const SDRS = ["Emma", "Laura"] as const;
export type Sdr = (typeof SDRS)[number];

export const LEVELS = ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3"];

export const DRAFT_STATUS_LABEL: Record<string, string> = {
  pendiente_validar: "Pendiente de validar",
  validado: "Validado",
  enviado: "Enviado",
  no_enviado: "No enviado",
};
/** Semáforo: pendiente = ámbar, validado/enviado = verde, no_enviado = rojo. */
export const DRAFT_STATUS_TONE: Record<string, "ok" | "warn" | "bad"> = {
  pendiente_validar: "warn",
  validado: "ok",
  enviado: "ok",
  no_enviado: "bad",
};

export const OUTCOME_LABEL: Record<string, string> = {
  no_contesta: "No contesta",
  no_interesado: "No interesado",
  mal_timing: "Mal momento",
  ya_tiene_proveedor: "Ya tiene proveedor",
  seguimiento: "Seguimiento",
  reunion: "Reunión",
};
export const ORIGIN_LABEL: Record<string, string> = {
  scored: "Puntuada",
  control: "Control",
  manual: "Manual",
  puntuada: "Puntuada",
  alerta: "Alerta",
  inbound: "Inbound",
};
