-- Esquema inicial (Supabase / Postgres). Idempotente.
-- RLS activado: solo el usuario autenticado del dashboard (un único usuario) accede por la API de Supabase.
-- El motor (GitHub Actions) usa DATABASE_URL (rol postgres) y no pasa por RLS.

create table if not exists companies (
  hs_id text primary key, name text, domain text, cif text, cif_norm text, name_norm text,
  target_market text, proveedor text, pais text, status text, tipo_de_contacto text,
  last_activity_at timestamptz, updated_at timestamptz default now()
);
create table if not exists contacts (
  hs_id text primary key, company_hs_id text references companies(hs_id), email text,
  cargo_icp text, phones text[], linkedin_url text, email_bounced boolean default false,
  excluded boolean default false, exclusion_reason text, updated_at timestamptz default now()
);
create index if not exists contacts_company_idx on contacts(company_hs_id);

create table if not exists signals (
  id bigserial primary key, company_hs_id text, contact_hs_id text,
  kind text not null check (kind in ('engagement','intent')), type text not null,
  object_key text not null default '', occurred_at timestamptz not null,
  points_raw numeric not null, source text, meta jsonb default '{}',
  day date generated always as ((occurred_at at time zone 'UTC')::date) stored,
  unique (contact_hs_id, kind, type, object_key, day)          -- una vez al día
);
create index if not exists signals_company_idx on signals(company_hs_id, occurred_at desc);

create table if not exists company_scores_daily (
  date date, company_hs_id text, fit numeric, fit_tier text, engagement numeric, intent numeric,
  intent_tier int, intent_velocity numeric, priority text, action text,
  best_contact text, missing_decision_maker boolean, breakdown jsonb, config_version text,
  primary key (date, company_hs_id)
);
create table if not exists contact_scores_daily (
  date date, contact_hs_id text, company_hs_id text, persona numeric, breakdown jsonb,
  primary key (date, contact_hs_id)
);

create table if not exists weekly_drafts (
  id bigserial primary key, week date unique not null,
  status text not null default 'pendiente_validar'
    check (status in ('pendiente_validar','validado','enviado','no_enviado')),
  created_at timestamptz default now(), validated_at timestamptz, sent_at timestamptz
);
create table if not exists weekly_assignments (
  id bigserial primary key, draft_id bigint references weekly_drafts(id) on delete cascade,
  company_hs_id text not null, sdr text not null, rank int, is_control boolean default false,
  origin text default 'scored' check (origin in ('scored','control','manual')),
  claude jsonb, user_edit text, edit_log jsonb default '[]', removed boolean default false,
  unique (draft_id, company_hs_id)
);
create table if not exists alerts_sent (
  id bigserial primary key, company_hs_id text, reason text, sdr text, sent_at timestamptz default now()
);
create table if not exists call_outcomes (
  id bigserial primary key, company_hs_id text, contact_hs_id text, sdr text, at timestamptz,
  outcome text check (outcome in ('no_contesta','no_interesado','mal_timing','ya_tiene_proveedor','seguimiento','reunion'))
);
create table if not exists freezes (
  company_hs_id text primary key, kind text check (kind in ('no_interesa','ahora_no')), until timestamptz
);

create table if not exists venzo_imports (id bigserial primary key, file text, loaded_at timestamptz default now(), rows int);
create table if not exists venzo_rows (
  id bigserial primary key, import_id bigint references venzo_imports(id) on delete cascade,
  raw jsonb, company_hs_id text, match_method text check (match_method in ('cif','dominio','nombre','ninguno')),
  match_confidence numeric
);
create table if not exists venzo_review (
  id bigserial primary key, venzo_row_id bigint references venzo_rows(id) on delete cascade,
  candidates jsonb, decision text, decided_at timestamptz
);
create table if not exists opportunities (
  id text primary key, company_hs_id text, stage text, status text, loss_reason text,
  opened_at date, closed_at date, origin text, raw jsonb
);
create table if not exists url_classification (
  url text primary key, category_rule text, block text, points numeric, source text default 'claude', classified_at timestamptz default now()
);
create table if not exists change_log (
  id bigserial primary key, at timestamptz default now(), object_type text, object_id text,
  property text, old_value text, new_value text, mode text check (mode in ('dry-run','apply'))
);

do $$ declare t text; begin
  for t in select unnest(array['companies','contacts','signals','company_scores_daily','contact_scores_daily',
    'weekly_drafts','weekly_assignments','alerts_sent','call_outcomes','freezes','venzo_imports','venzo_rows',
    'venzo_review','opportunities','url_classification','change_log']) loop
    execute format('alter table %I enable row level security', t);
    execute format('drop policy if exists dashboard_user on %I', t);
    execute format('create policy dashboard_user on %I for all to authenticated using (true) with check (true)', t);
  end loop;
end $$;
