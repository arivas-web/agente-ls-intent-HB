-- Candidatos ordenados de cada borrador (para "sustituir por la siguiente de la lista" en el dashboard).
create table if not exists draft_candidates (
  draft_id bigint references weekly_drafts(id) on delete cascade,
  company_hs_id text not null, rank int not null, code text, fit numeric, intent numeric, engagement numeric,
  velocity numeric, is_control_pool boolean default false,
  primary key (draft_id, company_hs_id)
);
-- Informes mensuales en Markdown.
create table if not exists monthly_reports (
  month date primary key, markdown text not null, created_at timestamptz default now()
);
-- Ajustes de peso propuestos (NUNCA se aplican solos).
create table if not exists weight_proposals (
  id bigserial primary key, month date, proposal jsonb, status text default 'propuesta', created_at timestamptz default now()
);
-- Resumen de contexto de Venzo por empresa (gestiones recientes) para los resúmenes de Claude y el dashboard.
alter table opportunities add column if not exists amount numeric;
alter table opportunities add column if not exists last_management text;
alter table opportunities add column if not exists last_management_at date;
alter table opportunities add column if not exists status_norm text check (status_norm in ('abierta','ganada','perdida'));
-- Estado del avisador (envíos) y trazas del proceso.
create table if not exists job_runs (
  id bigserial primary key, job text, started_at timestamptz default now(), finished_at timestamptz,
  status text, detail text
);
alter table weekly_assignments add column if not exists sdr_original text;
alter table weekly_assignments add column if not exists added_manually boolean default false;
alter table company_scores_daily add column if not exists fit_points int;

do $$ declare t text; begin
  for t in select unnest(array['draft_candidates','monthly_reports','weight_proposals','job_runs']) loop
    execute format('alter table %I enable row level security', t);
    execute format('drop policy if exists dashboard_user on %I', t);
    execute format('create policy dashboard_user on %I for all to authenticated using (true) with check (true)', t);
  end loop;
end $$;
