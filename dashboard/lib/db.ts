import type { SupabaseClient } from "@supabase/supabase-js";

export type Sb = SupabaseClient;
const PAGE = 1000;

/** Lee todas las filas de una consulta paginando (Supabase limita a 1000 por petición). */
export async function fetchAll<T>(build: (from: number, to: number) => PromiseLike<{ data: unknown; error: { message: string } | null }>): Promise<T[]> {
  const out: T[] = [];
  for (let from = 0; ; from += PAGE) {
    const { data, error } = await build(from, from + PAGE - 1);
    if (error) throw new Error(error.message);
    const rows = (data ?? []) as T[];
    out.push(...rows);
    if (rows.length < PAGE) break;
  }
  return out;
}

/** Ejecuta una consulta `in (...)` por trozos para no exceder la longitud de la URL. */
export async function inChunks<T>(ids: string[], fn: (chunk: string[]) => Promise<T[]>, size = 100): Promise<T[]> {
  const uniq = [...new Set(ids.filter(Boolean))];
  const out: T[] = [];
  for (let i = 0; i < uniq.length; i += size) out.push(...(await fn(uniq.slice(i, i + size))));
  return out;
}

export async function latestScoreDate(sb: Sb): Promise<string | null> {
  const { data, error } = await sb.from("company_scores_daily").select("date").order("date", { ascending: false }).limit(1);
  if (error) throw new Error(error.message);
  return data?.[0]?.date ?? null;
}

/** Foto más reciente de puntuaciones para un conjunto de empresas. */
export async function latestScores(sb: Sb, ids: string[], date?: string | null) {
  const d = date ?? (await latestScoreDate(sb));
  const map = new Map<string, import("./types").ScoreRow>();
  if (!d) return map;
  const rows = await inChunks<import("./types").ScoreRow>(ids, async (chunk) => {
    const { data, error } = await sb.from("company_scores_daily").select("*").eq("date", d).in("company_hs_id", chunk);
    if (error) throw new Error(error.message);
    return (data ?? []) as import("./types").ScoreRow[];
  });
  rows.forEach((r) => map.set(r.company_hs_id, r));
  return map;
}

export async function companiesByIds(sb: Sb, ids: string[]) {
  const map = new Map<string, import("./types").Company>();
  const rows = await inChunks<import("./types").Company>(ids, async (chunk) => {
    const { data, error } = await sb.from("companies").select("*").in("hs_id", chunk);
    if (error) throw new Error(error.message);
    return (data ?? []) as import("./types").Company[];
  });
  rows.forEach((r) => map.set(r.hs_id, r));
  return map;
}

/** Escapa caracteres especiales de ilike / or() de PostgREST. */
export function safeLike(q: string): string {
  return q.replace(/[%_,()*\\]/g, " ").trim();
}
