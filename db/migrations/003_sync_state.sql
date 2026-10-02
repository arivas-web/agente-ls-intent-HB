-- Último valor escrito (o que se escribiría) en HubSpot por empresa, para escribir solo lo que cambia.
create table if not exists hubspot_sync_state (
  company_hs_id text primary key, props jsonb not null, synced_at timestamptz default now()
);
alter table hubspot_sync_state enable row level security;
drop policy if exists dashboard_user on hubspot_sync_state;
create policy dashboard_user on hubspot_sync_state for all to authenticated using (true) with check (true);
