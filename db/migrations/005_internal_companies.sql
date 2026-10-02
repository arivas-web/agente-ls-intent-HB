-- Empresas propias (Visual Trans, Visual Microsystems, Docuten): fuera de reparto, alertas, puntuaciones y Cuentas.
alter table companies add column if not exists internal boolean not null default false;

create or replace view company_overview with (security_invoker = true) as
select c.hs_id, c.name, c.domain, c.target_market, c.proveedor, c.pais, c.status, c.last_activity_at,
       s.date as score_date, s.fit, s.fit_tier, s.engagement, s.intent, s.intent_tier, s.intent_velocity,
       s.priority, s.action, s.missing_decision_maker,
       g.last_signal_at,
       coalesce(g.signals_7d, 0)  as signals_7d,
       coalesce(g.signals_30d, 0) as signals_30d,
       coalesce(g.visits_30d, 0)  as visits_30d,
       coalesce(g.email_clicks_30d, 0) as email_clicks_30d,
       coalesce(g.active_contacts_30d, 0) as active_contacts_30d
from companies c
left join company_scores_daily s
  on s.company_hs_id = c.hs_id and s.date = (select max(date) from company_scores_daily)
left join (
  select company_hs_id,
         max(occurred_at) filter (where points_raw <> 0) as last_signal_at,
         count(*) filter (where points_raw <> 0 and occurred_at > now() - interval '7 days')  as signals_7d,
         count(*) filter (where points_raw <> 0 and occurred_at > now() - interval '30 days') as signals_30d,
         count(*) filter (where type = 'web_visit' and points_raw <> 0 and occurred_at > now() - interval '30 days') as visits_30d,
         count(*) filter (where type = 'email_click' and occurred_at > now() - interval '30 days') as email_clicks_30d,
         count(distinct contact_hs_id) filter (where points_raw <> 0 and occurred_at > now() - interval '30 days') as active_contacts_30d
  from signals group by company_hs_id
) g on g.company_hs_id = c.hs_id
where not c.internal;
